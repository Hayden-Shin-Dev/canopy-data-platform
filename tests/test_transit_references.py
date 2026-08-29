from pathlib import Path

import pandas as pd
import pytest

from src.transit_context.references import normalize_bus_route_stops, normalize_bus_stops


def test_bus_normalization_requires_explicit_mapping() -> None:
    frame = pd.DataFrame({"city": [1], "stop": ["s1"], "name": ["정류장"], "lat": [37.5], "lon": [127.0]})
    mapping = {"city_code": "city", "stop_id": "stop", "stop_name": "name", "latitude": "lat", "longitude": "lon"}
    result = normalize_bus_stops(frame, mapping, source="fixture")
    assert result.loc[0, "stop_id"] == "s1"


def test_bus_route_normalization_drops_invalid_coordinates() -> None:
    frame = pd.DataFrame(
        {
            "city": [1, 1], "route": ["r1", "r1"], "no": ["10", "10"], "stop": ["s1", "s2"],
            "seq": [1, 2], "lat": [37.5, 120], "lon": [127, 127],
        }
    )
    mapping = {"city_code": "city", "route_id": "route", "route_no": "no", "stop_id": "stop", "stop_sequence": "seq", "latitude": "lat", "longitude": "lon"}
    result = normalize_bus_route_stops(frame, mapping, source="fixture")
    assert result["stop_id"].tolist() == ["s1"]


def test_bus_mapping_missing_field_is_error() -> None:
    with pytest.raises(ValueError, match="필드"):
        normalize_bus_stops(pd.DataFrame({"id": [1]}), {"stop_id": "id"}, source="fixture")
