"""Build versioned Transit Context reference tables from inspected source files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from .normalization import (
    normalize_korail_stations,
    normalize_subway_stations,
    normalize_subway_timetable,
)


def normalize_bus_stops(frame: pd.DataFrame, columns: Mapping[str, str], *, source: str) -> pd.DataFrame:
    """Normalize a bus stop response using an explicit, inspected field mapping."""

    required = {"city_code", "stop_id", "stop_name", "latitude", "longitude"}
    missing_mapping = sorted(required - set(columns))
    if missing_mapping:
        raise ValueError(f"버스 정류장 매핑에 필요한 필드가 없습니다: {missing_mapping}")
    missing_columns = sorted(set(columns.values()) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"버스 정류장 응답에 실제 필드가 없습니다: {missing_columns}")
    result = pd.DataFrame(
        {
            "city_code": frame[columns["city_code"]].astype("string").str.strip(),
            "stop_id": frame[columns["stop_id"]].astype("string").str.strip(),
            "stop_name": frame[columns["stop_name"]].astype("string").str.strip(),
            "latitude": pd.to_numeric(frame[columns["latitude"]], errors="coerce"),
            "longitude": pd.to_numeric(frame[columns["longitude"]], errors="coerce"),
            "source": source,
        }
    )
    valid = result["stop_id"].notna() & result["latitude"].between(-90, 90) & result["longitude"].between(-180, 180)
    return result[valid].drop_duplicates(["city_code", "stop_id"], keep="first").reset_index(drop=True)


def normalize_bus_route_stops(frame: pd.DataFrame, columns: Mapping[str, str], *, source: str) -> pd.DataFrame:
    """Normalize ordered bus route-stop rows using an explicit field mapping."""

    required = {"city_code", "route_id", "route_no", "stop_id", "stop_sequence", "latitude", "longitude"}
    missing_mapping = sorted(required - set(columns))
    if missing_mapping:
        raise ValueError(f"버스 노선 정류장 매핑에 필요한 필드가 없습니다: {missing_mapping}")
    missing_columns = sorted(set(columns.values()) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"버스 노선 응답에 실제 필드가 없습니다: {missing_columns}")
    result = pd.DataFrame(
        {
            "city_code": frame[columns["city_code"]].astype("string").str.strip(),
            "route_id": frame[columns["route_id"]].astype("string").str.strip(),
            "route_no": frame[columns["route_no"]].astype("string").str.strip(),
            "stop_id": frame[columns["stop_id"]].astype("string").str.strip(),
            "stop_sequence": pd.to_numeric(frame[columns["stop_sequence"]], errors="coerce"),
            "latitude": pd.to_numeric(frame[columns["latitude"]], errors="coerce"),
            "longitude": pd.to_numeric(frame[columns["longitude"]], errors="coerce"),
            "source": source,
        }
    )
    valid = (
        result["route_id"].notna()
        & result["stop_id"].notna()
        & result["stop_sequence"].notna()
        & result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    )
    return result[valid].drop_duplicates(["city_code", "route_id", "stop_sequence"], keep="first").reset_index(drop=True)


def build_reference_files(
    *,
    output_dir: str | Path,
    subway_coordinates: str | Path,
    subway_timetable: str | Path,
    korail_stations: str | Path,
) -> dict[str, object]:
    """Write normalized rail references and a transparent station-name mismatch report."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stations = normalize_subway_stations(subway_coordinates)
    timetable = normalize_subway_timetable(subway_timetable)
    korail = normalize_korail_stations(korail_stations)
    stations.to_csv(output / "subway_stations.csv", index=False, encoding="utf-8-sig")
    timetable.to_csv(output / "subway_timetable.csv", index=False, encoding="utf-8-sig")
    korail.to_csv(output / "korail_stations.csv", index=False, encoding="utf-8-sig")

    station_keys = stations[["line", "normalized_station_name"]].drop_duplicates()
    timetable_keys = timetable[["line", "normalized_station_name"]].drop_duplicates()
    unmatched = timetable_keys.merge(station_keys, on=["line", "normalized_station_name"], how="left", indicator=True)
    unmatched = unmatched[unmatched["_merge"] == "left_only"].drop(columns="_merge")
    unmatched.to_csv(output / "subway_station_unmatched.csv", index=False, encoding="utf-8-sig")

    summary = {
        "subway_stations": int(len(stations)),
        "subway_timetable_rows": int(len(timetable)),
        "korail_stations": int(len(korail)),
        "subway_unmatched_station_keys": int(len(unmatched)),
        "sources": {
            "subway_coordinates": str(subway_coordinates),
            "subway_timetable": str(subway_timetable),
            "korail_stations": str(korail_stations),
        },
    }
    (output / "reference_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
