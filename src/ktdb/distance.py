"""행정동 대표좌표를 이용한 선택적 OD 직선거리 계산."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from src.common.geo import haversine_distance_km


CENTROID_COLUMNS = ("admin_dong", "latitude", "longitude")


def validate_centroid_table(centroids: pd.DataFrame) -> None:
    """좌표 테이블의 필수 컬럼과 좌표 범위를 확인한다."""

    missing = sorted(set(CENTROID_COLUMNS) - set(centroids.columns))
    if missing:
        raise ValueError(f"centroid 테이블에 필요한 컬럼이 없습니다: {missing}")
    if centroids["admin_dong"].duplicated().any():
        raise ValueError("admin_dong은 좌표 테이블에서 유일해야 합니다")
    for row in centroids.itertuples(index=False):
        latitude = getattr(row, "latitude")
        longitude = getattr(row, "longitude")
        if pd.isna(latitude) or pd.isna(longitude):
            continue
        # geo 함수가 범위와 유한성 검사를 담당한다.
        haversine_distance_km(float(latitude), float(longitude), float(latitude), float(longitude))


def add_od_distance(
    frame: pd.DataFrame,
    centroids: pd.DataFrame,
    *,
    origin_column: str = "origin_admin_dong",
    destination_column: str = "destination_admin_dong",
    centroid_columns: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """출발·도착 행정동을 매칭해 ``od_straight_distance_km``를 추가한다.

    매칭되지 않는 행은 좌표를 추정하지 않고 ``pd.NA``로 남긴다.
    """

    required = {origin_column, destination_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"거리 계산에 필요한 frame 컬럼이 없습니다: {missing}")
    rename = dict(centroid_columns or {})
    table = centroids.rename(columns=rename).copy()
    validate_centroid_table(table)
    lookup = table.set_index("admin_dong")
    result = frame.copy()
    origin_lat = result[origin_column].map(lookup["latitude"])
    origin_lon = result[origin_column].map(lookup["longitude"])
    destination_lat = result[destination_column].map(lookup["latitude"])
    destination_lon = result[destination_column].map(lookup["longitude"])
    distances: list[float | pd._libs.missing.NAType] = []
    for values in zip(origin_lat, origin_lon, destination_lat, destination_lon, strict=True):
        if any(pd.isna(value) for value in values):
            distances.append(pd.NA)
            continue
        distances.append(haversine_distance_km(*(float(value) for value in values)))
    result["od_straight_distance_km"] = pd.array(distances, dtype="Float64")
    return result
