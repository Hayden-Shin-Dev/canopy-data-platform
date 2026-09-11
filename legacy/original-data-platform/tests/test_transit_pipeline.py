import pandas as pd
import pytest

from src.transit_context.pipeline import apply_resolver_to_frame


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "window_id": ["w1"], "walk_probability": [0.05], "bike_probability": [0.05],
        "car_probability": [0.8], "bus_probability": [0.05], "rail_probability": [0.05],
    })


def test_pipeline_preserves_probability_columns_and_adds_decision() -> None:
    result = apply_resolver_to_frame(_frame())
    assert result.loc[0, "ml_predicted_mode"] == "car"
    assert result.loc[0, "final_mode"] == "car"
    assert "decision_status" in result


def test_pipeline_refuses_korean_context_for_geolife() -> None:
    with pytest.raises(ValueError, match="GeoLife"):
        apply_resolver_to_frame(_frame(), source_kind="geolife")
