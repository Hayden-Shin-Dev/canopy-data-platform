import pandas as pd

from src.transit_context.seoul_api import merge_line_metadata, normalize_line


def test_normalize_observed_line_formats() -> None:
    assert normalize_line("01호선") == "1"
    assert normalize_line("1") == "1"


def test_merge_line_metadata_reports_unmatched_without_fuzzy_join() -> None:
    coords = pd.DataFrame({"station_id": ["c1"], "station_name": ["서울"], "normalized_station_name": ["서울"], "line": ["1"], "latitude": [37.5], "longitude": [127.0], "source": ["coords"]})
    api = pd.DataFrame({"station_id": ["a1", "a2"], "station_name": ["서울역", "없는역"], "normalized_station_name": ["서울", "없는역"], "line": ["01호선", "01호선"], "external_code": ["1", "2"], "source": ["api", "api"]})
    matched, unmatched = merge_line_metadata(coords, api)
    assert len(matched) == 1
    assert len(unmatched) == 1
