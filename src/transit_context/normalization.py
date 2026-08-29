"""Normalize supplied Korean rail and subway files without changing the originals."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


SUBWAY_COORD_COLUMNS = {
    "line": "호선",
    "station_id": "고유역번호(외부역코드)",
    "station_name": "역명",
    "latitude": "위도",
    "longitude": "경도",
}
SUBWAY_TIMETABLE_COLUMNS = {
    "line": "호선",
    "station_id": "역사코드",
    "station_name": "역사명",
    "service_type_raw": "주중주말",
    "direction": "방향",
    "arrival_time": "열차도착시간",
    "departure_time": "열차출발시간",
}
KORAIL_COLUMNS = {
    "region": "지역본부",
    "station_name": "역명",
    "latitude": "위도",
    "longitude": "경도",
}


def read_korean_csv(path: str | Path, *, nrows: int | None = None) -> pd.DataFrame:
    """Read a supplied CSV using BOM-aware UTF-8 or the observed CP949 encoding."""

    source = Path(path)
    errors: list[str] = []
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(source, encoding=encoding, nrows=nrows, low_memory=False)
        except (UnicodeDecodeError, UnicodeError) as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeError(f"지원하는 인코딩으로 CSV를 읽지 못했습니다: {source}; {'; '.join(errors)}")


def _require_columns(frame: pd.DataFrame, columns: dict[str, str], source: Path) -> None:
    missing = [column for column in columns.values() if column not in frame.columns]
    if missing:
        raise ValueError(f"{source.name}에 필요한 실제 컬럼이 없습니다: {missing}")


def normalize_station_name(value: object) -> str:
    """Normalize spacing and a terminal Korean station suffix for exact joins."""

    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = re.sub(r"\s+", "", text)
    if text.endswith("역") and not text.endswith("역사"):
        text = text[:-1]
    return text


def _valid_coordinates(frame: pd.DataFrame) -> pd.Series:
    latitude = pd.to_numeric(frame["latitude"], errors="coerce")
    longitude = pd.to_numeric(frame["longitude"], errors="coerce")
    return latitude.between(-90, 90) & longitude.between(-180, 180)


def normalize_subway_stations(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    raw = read_korean_csv(source)
    _require_columns(raw, SUBWAY_COORD_COLUMNS, source)
    result = pd.DataFrame(
        {
            "station_id": raw[SUBWAY_COORD_COLUMNS["station_id"]].astype("string").str.strip(),
            "station_name": raw[SUBWAY_COORD_COLUMNS["station_name"]].astype("string").str.strip(),
            "normalized_station_name": raw[SUBWAY_COORD_COLUMNS["station_name"]].map(normalize_station_name),
            "line": raw[SUBWAY_COORD_COLUMNS["line"]].astype("string").str.strip(),
            "latitude": pd.to_numeric(raw[SUBWAY_COORD_COLUMNS["latitude"]], errors="coerce"),
            "longitude": pd.to_numeric(raw[SUBWAY_COORD_COLUMNS["longitude"]], errors="coerce"),
            "source": source.name,
        }
    )
    result = result[_valid_coordinates(result) & result["station_id"].notna() & result["station_name"].notna()]
    result = result.drop_duplicates(["line", "station_id"], keep="first").reset_index(drop=True)
    return result


def normalize_subway_timetable(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    raw = read_korean_csv(source)
    _require_columns(raw, SUBWAY_TIMETABLE_COLUMNS, source)
    service_map = {"DAY": "weekday", "SAT": "saturday", "END": "sunday_or_holiday"}
    raw_service = raw[SUBWAY_TIMETABLE_COLUMNS["service_type_raw"]].astype("string").str.strip().str.upper()
    result = pd.DataFrame(
        {
            "line": raw[SUBWAY_TIMETABLE_COLUMNS["line"]].astype("string").str.strip(),
            "station_id": raw[SUBWAY_TIMETABLE_COLUMNS["station_id"]].astype("string").str.strip(),
            "station_name": raw[SUBWAY_TIMETABLE_COLUMNS["station_name"]].astype("string").str.strip(),
            "normalized_station_name": raw[SUBWAY_TIMETABLE_COLUMNS["station_name"]].map(normalize_station_name),
            "direction": raw[SUBWAY_TIMETABLE_COLUMNS["direction"]].astype("string").str.strip(),
            "service_type": raw_service.map(service_map).fillna(raw_service.str.lower()),
            "service_type_raw": raw_service,
            "arrival_time": raw[SUBWAY_TIMETABLE_COLUMNS["arrival_time"]].astype("string").replace("<NA>", pd.NA),
            "departure_time": raw[SUBWAY_TIMETABLE_COLUMNS["departure_time"]].astype("string").replace("<NA>", pd.NA),
            "source": source.name,
        }
    )
    result = result[result["station_id"].notna() & result["station_name"].notna()].reset_index(drop=True)
    return result


def normalize_korail_stations(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    raw = read_korean_csv(source)
    _require_columns(raw, KORAIL_COLUMNS, source)
    names = raw[KORAIL_COLUMNS["station_name"]].astype("string").str.strip()
    result = pd.DataFrame(
        {
            "station_id": names.map(lambda value: f"korail:{normalize_station_name(value)}"),
            "station_name": names,
            "normalized_station_name": names.map(normalize_station_name),
            "latitude": pd.to_numeric(raw[KORAIL_COLUMNS["latitude"]], errors="coerce"),
            "longitude": pd.to_numeric(raw[KORAIL_COLUMNS["longitude"]], errors="coerce"),
            "source": source.name,
            "region": raw[KORAIL_COLUMNS["region"]].astype("string").str.strip(),
        }
    )
    result = result[_valid_coordinates(result) & result["normalized_station_name"].ne("")]
    return result.drop_duplicates("station_id", keep="first").reset_index(drop=True)
