from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.distance import add_od_distance, validate_centroid_table


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
