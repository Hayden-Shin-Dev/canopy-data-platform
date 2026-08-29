import pandas as pd

from src.transit_context.evidence import bus_context, sequence_score, subway_context
from src.transit_context.spatial import GeoPointIndex


def test_sequence_score_accepts_reverse_route_order() -> None:
    route = pd.DataFrame({"stop_id": ["a", "b", "c"], "stop_sequence": [1, 2, 3]})
    assert sequence_score(["c", "b", "a"], route) == 1.0


def test_bus_context_requires_route_evidence_for_high_score() -> None:
    stops = pd.DataFrame({"stop_id": ["a", "b"], "latitude": [37.5, 37.5005], "longitude": [127, 127]})
    routes = pd.DataFrame({"route_id": ["r1", "r1"], "route_no": ["10", "10"], "stop_id": ["a", "b"], "stop_sequence": [1, 2], "latitude": [37.5, 37.5005], "longitude": [127, 127]})
    result = bus_context(start_latitude=37.5, start_longitude=127, end_latitude=37.5005, end_longitude=127, bus_stop_index=GeoPointIndex.from_frame(stops), bus_stops=stops, bus_route_stops=routes, observed_stop_ids=["a", "b"])
    assert result["matched_bus_route_id"] == "r1"
    assert result["bus_sequence_score"] == 1.0
    assert 0 <= result["bus_context_score"] <= 1


def test_subway_same_line_produces_line_evidence() -> None:
    stations = pd.DataFrame({"station_id": ["1", "2"], "line": ["1", "1"], "latitude": [37.5, 37.5005], "longitude": [127, 127], "station_name": ["A", "B"]})
    result = subway_context(start_latitude=37.5, start_longitude=127, end_latitude=37.5005, end_longitude=127, station_index=GeoPointIndex.from_frame(stations), stations=stations, timetable_compatible=True)
    assert result["subway_line_score"] == 1.0
    assert result["matched_subway_line"] == "1"
