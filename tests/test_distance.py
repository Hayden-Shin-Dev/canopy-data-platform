from __future__ import annotations

import pandas as pd
import pytest
from pyproj import Transformer

from src.ktdb.distance import (
    add_od_distance,
    add_projected_od_distance,
    transform_to_wgs84,
    validate_centroid_table,
)


def test_add_od_distance_uses_centroids_and_keeps_unmatched_missing() -> None:
    frame = pd.DataFrame(
        {
            "origin_admin_dong": ["출발동", "없는동"],
            "destination_admin_dong": ["도착동", "도착동"],
        }
    )
    centroids = pd.DataFrame(
        {
            "admin_dong": ["출발동", "도착동"],
            "latitude": [0.0, 0.0],
            "longitude": [0.0, 1.0],
        }
    )

    result = add_od_distance(frame, centroids)

    assert result.loc[0, "od_straight_distance_km"] == pytest.approx(111.195, rel=1e-4)
    assert pd.isna(result.loc[1, "od_straight_distance_km"])


def test_validate_centroid_table_rejects_duplicate_keys() -> None:
    centroids = pd.DataFrame(
        {
            "admin_dong": ["중복동", "중복동"],
            "latitude": [37.0, 37.1],
            "longitude": [127.0, 127.1],
        }
    )

    with pytest.raises(ValueError, match="유일"):
        validate_centroid_table(centroids)


def test_transform_to_wgs84_converts_sgis_epsg_5179_coordinate() -> None:
    longitude, latitude = transform_to_wgs84(953808.5, 1952441.25)

    assert longitude == pytest.approx(126.976925, abs=1e-6)
    assert latitude == pytest.approx(37.570183, abs=1e-6)


def test_add_projected_od_distance_uses_wgs84_haversine_and_keeps_missing() -> None:
    to_sgis = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
    origin_x, origin_y = to_sgis.transform(127.0, 37.5)
    destination_x, destination_y = to_sgis.transform(127.01, 37.5)
    frame = pd.DataFrame(
        {
            "origin_x": [origin_x, pd.NA],
            "origin_y": [origin_y, pd.NA],
            "destination_x": [destination_x, destination_x],
            "destination_y": [destination_y, destination_y],
        }
    )

    result = add_projected_od_distance(frame)

    assert result.loc[0, "od_straight_distance_km"] == pytest.approx(0.882, rel=1e-3)
    assert pd.isna(result.loc[1, "od_straight_distance_km"])
