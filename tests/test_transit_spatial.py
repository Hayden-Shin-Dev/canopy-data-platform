import pandas as pd
import pytest

from src.transit_context.spatial import GeoPointIndex


def test_spatial_index_returns_sorted_nearby_points() -> None:
    index = GeoPointIndex.from_frame(pd.DataFrame({"id": ["a", "b"], "latitude": [37.5, 37.51], "longitude": [127, 127]}))
    result = index.query(37.5, 127, radius_m=2_000)
    assert result["id"].tolist() == ["a", "b"]
    assert result["distance_m"].iloc[0] == pytest.approx(0, abs=1)


def test_spatial_index_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValueError, match="유효하지 않은"):
        GeoPointIndex.from_frame(pd.DataFrame({"latitude": [91], "longitude": [127]}))
