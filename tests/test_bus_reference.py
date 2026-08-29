import pandas as pd

from src.transit_context.bus_reference import join_route_stops, match_bus_stops


def _national() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stop_id": ["N-1", "N-2", "N-3"],
            "stop_name": ["Alpha", "Duplicate", "Duplicate"],
            "latitude": [37.1, 37.2, 37.3],
            "longitude": [127.1, 127.2, 127.3],
            "city_code": ["24", "24", "24"],
            "city_name": ["Gwangju", "Gwangju", "Gwangju"],
            "managing_city_name": ["BIS", "BIS", "BIS"],
            "normalized_stop_name": ["alpha", "duplicate", "duplicate"],
            "valid_coordinate": [True, True, True],
        }
    )


def test_name_region_match_requires_unique_candidate() -> None:
    api = pd.DataFrame({"stop_id": ["api-1", "api-2"], "stop_name": ["Alpha", "Duplicate"], "city_code": ["29", "29"]})
    routes = pd.DataFrame({"city_code": ["29"], "ctpv_nm": ["Gwangju"]})
    matched, unmatched, summary = match_bus_stops(api, _national(), routes)
    assert matched["stop_id"].tolist() == ["api-1"]
    assert unmatched["stop_id"].tolist() == ["api-2"]
    assert summary["name_region_match_count"] == 1


def test_id_match_is_preferred_over_name() -> None:
    national = _national()
    national.loc[0, "stop_name"] = "Other Name"
    api = pd.DataFrame({"stop_id": ["N-1"], "stop_name": ["Alpha"], "city_code": ["29"]})
    matched, unmatched, summary = match_bus_stops(api, national)
    assert unmatched.empty
    assert matched.loc[0, "match_type"] == "id_exact"
    assert summary["exact_id_match_count"] == 1


def test_route_join_keeps_only_coordinate_resolved_stops() -> None:
    matched = pd.DataFrame({"stop_id": ["s1"], "latitude": [37.1], "longitude": [127.1], "coordinate_source": ["national_bus_stop_file"], "match_type": ["id_exact"]})
    routes = pd.DataFrame({"route_id": ["r1", "r1"], "stop_id": ["s1", "s2"], "stop_sequence": [1, 2]})
    joined, unmatched = join_route_stops(routes, matched)
    assert joined["stop_id"].tolist() == ["s1"]
    assert unmatched["stop_id"].tolist() == ["s2"]
