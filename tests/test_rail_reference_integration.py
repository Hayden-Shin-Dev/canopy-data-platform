import pandas as pd

from src.transit_context.evidence import korail_context, subway_context
from src.transit_context.spatial import GeoPointIndex


def test_real_seoul_subway_line_one_endpoint_pair() -> None:
    # Coordinates and IDs are copied from the generated official-reference rows.
    stations = pd.DataFrame(
        {
            "station_id": ["159", "158", "157"],
            "station_name": ["동묘앞", "청량리", "제기동"],
            "line": ["1", "1", "1"],
            "latitude": [37.573265, 37.580148, 37.578116],
            "longitude": [127.016459, 127.045063, 127.034902],
        }
    )
    timetable = pd.DataFrame({"line": ["1", "1", "1"], "station_id": ["159", "158", "157"], "service_type": ["weekday"] * 3})
    endpoint_rows = timetable[timetable["station_id"].isin(["159", "157"])]
    context = subway_context(
        start_latitude=37.573265,
        start_longitude=127.016459,
        end_latitude=37.578116,
        end_longitude=127.034902,
        station_index=GeoPointIndex.from_frame(stations),
        stations=stations,
        timetable_compatible=(len(endpoint_rows) == 2 and set(endpoint_rows["line"]) == {"1"}),
    )
    assert context["subway_start_station_id"] == "159"
    assert context["subway_end_station_id"] == "157"
    assert context["matched_subway_line"] == "1"
    assert context["subway_timetable_score"] == 1.0


def test_real_korail_seoul_yongsan_endpoint_pair() -> None:
    stations = pd.DataFrame(
        {
            "station_id": ["korail:서울", "korail:용산"],
            "latitude": [37.55473, 37.52991],
            "longitude": [126.9708, 126.9648],
        }
    )
    context = korail_context(
        start_latitude=37.55473,
        start_longitude=126.9708,
        end_latitude=37.52991,
        end_longitude=126.9648,
        station_index=GeoPointIndex.from_frame(stations),
        ml_rail_probability=0.8,
        movement_score=1.0,
    )
    assert context["matched_train_start_station"] == "korail:서울"
    assert context["matched_train_end_station"] == "korail:용산"
    assert context["train_context_score"] > 0.5
