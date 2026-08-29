import pandas as pd

from src.transit_context.trip import build_trip_context


def test_trip_context_aggregates_adjacent_windows() -> None:
    frame = pd.DataFrame({
        "trip_id": ["t1", "t1"], "window_start": ["2024-01-01 09:00", "2024-01-01 09:02"],
        "bus_context_score": [0.2, 0.8], "subway_context_score": [0.0, 0.1], "train_context_score": [0.0, 0.0],
    })
    result = build_trip_context(frame)
    assert result.loc[0, "window_count"] == 2
    assert result.loc[0, "bus_context_score"] == 0.8
    assert result.loc[0, "trip_context_status"] == "supported"
