from pathlib import Path

import pandas as pd

from src.transit_context.evidence import bus_context, korail_context, subway_context
from src.transit_context.resolver import resolve_mode
from src.transit_context.spatial import GeoPointIndex


FIXTURE = Path(__file__).parent / "fixtures" / "seoul_bus_route_fixture.csv"


def test_seoul_bus_route_fixture_resolves_ordered_context() -> None:
    route_stops = pd.read_csv(FIXTURE, dtype={"route_id": str, "route_no": str, "stop_id": str})
    stops = route_stops.drop_duplicates("stop_id")
    context = bus_context(
        start_latitude=float(stops.iloc[0]["latitude"]),
        start_longitude=float(stops.iloc[0]["longitude"]),
        end_latitude=float(stops.iloc[3]["latitude"]),
        end_longitude=float(stops.iloc[3]["longitude"]),
        bus_stop_index=GeoPointIndex.from_frame(stops),
        bus_stops=stops,
        bus_route_stops=route_stops,
        observed_stop_ids=route_stops["stop_id"].tolist(),
    )
    decision = resolve_mode({"walk": 0.1, "bike": 0.05, "car": 0.15, "bus": 0.6, "rail": 0.1}, context=context)
    assert context["matched_bus_route_id"] == "121900014"
    assert context["bus_sequence_score"] == 1.0
    assert context["bus_context_score"] >= 0.7
    assert decision["final_mode"] == "bus"
