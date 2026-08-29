"""SGIS 2021 행정동 대표좌표 수집과 로컬 cache 관리."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .sgis import SGIS_YEAR, SgisApiError, SgisBoundaryRecord, SgisClient, parse_boundary_response


SGIS_SOURCE_CRS = "EPSG:5179"
REFERENCE_COLUMNS = ("adm_cd", "adm_nm", "x", "y", "source_crs", "reference_year")


def _write_raw_response(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _request_level(
    client: SgisClient,
    *,
    adm_cd: str | None,
    raw_response_dir: Path,
    year: str,
) -> list[SgisBoundaryRecord]:
    payload = client.request_boundary(adm_cd=adm_cd, low_search=1, year=year)
    filename = f"{adm_cd or 'national'}.geojson"
    _write_raw_response(raw_response_dir / filename, payload)
    return parse_boundary_response(payload)


def _validate_level(records: list[SgisBoundaryRecord], expected_length: int, label: str) -> None:
    invalid = sorted({record.adm_cd for record in records if len(record.adm_cd) != expected_length})
    if invalid:
        raise SgisApiError(f"SGIS {label} 코드 길이가 예상과 다릅니다: {invalid[:10]}")


def collect_admin_dong_centroids(
    client: SgisClient,
    *,
    raw_response_dir: Path,
    year: str = SGIS_YEAR,
) -> pd.DataFrame:
    """전국 하위 행정구역을 순회해 읍면동 reference를 만든다."""

    sido_records = _request_level(
        client,
        adm_cd=None,
        raw_response_dir=raw_response_dir,
        year=year,
    )
    _validate_level(sido_records, 2, "시도")

    sigungu_records: list[SgisBoundaryRecord] = []
    for sido in sido_records:
        sigungu_records.extend(
            _request_level(
                client,
                adm_cd=sido.adm_cd,
                raw_response_dir=raw_response_dir,
                year=year,
            )
        )
    _validate_level(sigungu_records, 5, "시군구")

    dong_records: list[SgisBoundaryRecord] = []
    for sigungu in sigungu_records:
        dong_records.extend(
            _request_level(
                client,
                adm_cd=sigungu.adm_cd,
                raw_response_dir=raw_response_dir,
                year=year,
            )
        )
    _validate_level(dong_records, 7, "읍면동")

    missing_coordinates = [record.adm_cd for record in dong_records if record.x is None or record.y is None]
    if missing_coordinates:
        raise SgisApiError(
            "SGIS 대표좌표 x/y가 없는 행정동이 있습니다. "
            f"polygon 좌표로 대체하지 않습니다: {missing_coordinates[:20]}"
        )

    frame = pd.DataFrame(
        [
            {
                "adm_cd": record.adm_cd,
                "adm_nm": record.adm_nm,
                "x": record.x,
                "y": record.y,
                "source_crs": SGIS_SOURCE_CRS,
                "reference_year": year,
            }
            for record in dong_records
        ],
        columns=REFERENCE_COLUMNS,
    )
    if frame["adm_cd"].duplicated().any():
        duplicates = frame.loc[frame["adm_cd"].duplicated(keep=False), "adm_cd"].unique().tolist()
        raise SgisApiError(f"SGIS 행정동 코드가 중복됩니다: {duplicates[:20]}")
    return frame.sort_values("adm_cd", kind="mergesort").reset_index(drop=True)


def validate_centroid_reference(frame: pd.DataFrame) -> None:
    missing = sorted(set(REFERENCE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"SGIS centroid reference에 필요한 컬럼이 없습니다: {missing}")
    if frame["adm_cd"].astype("string").duplicated().any():
        raise ValueError("SGIS adm_cd는 reference에서 유일해야 합니다")
    if frame[["x", "y"]].isna().any(axis=None):
        raise ValueError("SGIS centroid reference에 비어 있는 x/y가 있습니다")
    crs_values = set(frame["source_crs"].dropna().astype(str))
    if crs_values != {SGIS_SOURCE_CRS}:
        raise ValueError(f"지원하지 않는 SGIS 좌표계입니다: {sorted(crs_values)}")


def load_centroid_reference(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype={"adm_cd": "string"})
    validate_centroid_reference(frame)
    return frame


def write_centroid_reference(frame: pd.DataFrame, path: Path) -> None:
    validate_centroid_reference(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def load_or_collect_centroids(
    path: Path,
    *,
    client: SgisClient | None,
    raw_response_dir: Path,
    refresh: bool = False,
    year: str = SGIS_YEAR,
) -> pd.DataFrame:
    """기존 CSV를 우선 쓰고 refresh일 때만 SGIS를 다시 호출한다."""

    if path.is_file() and not refresh:
        return load_centroid_reference(path)
    if client is None:
        raise SgisApiError("SGIS reference를 수집하려면 인증 정보가 필요합니다")
    frame = collect_admin_dong_centroids(client, raw_response_dir=raw_response_dir, year=year)
    write_centroid_reference(frame, path)
    return frame
