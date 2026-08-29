from src.transit_context.resolver import resolve_mode


def test_weak_context_retains_ml_prediction() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.8, "bus": 0.05, "rail": 0.05})
    assert result["final_mode"] == "car"
    assert result["decision_status"] == "unchanged"


def test_strong_bus_context_can_correct_low_ml_bus_probability() -> None:
    result = resolve_mode({"walk": 0.1, "bike": 0.1, "car": 0.55, "bus": 0.1, "rail": 0.15}, context={"bus_context_score": 0.95})
    assert result["final_mode"] == "bus"
    assert result["correction_applied"] is True
    assert result["decision_status"] == "corrected"


def test_missing_context_is_reported_for_low_confidence() -> None:
    result = resolve_mode({"walk": 0.21, "bike": 0.2, "car": 0.2, "bus": 0.19, "rail": 0.2})
    assert result["decision_status"] == "insufficient_context"


def test_strong_train_evidence_marks_train_subtype() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.1, "bus": 0.1, "rail": 0.7}, context={"train_context_score": 0.9})
    assert result["final_mode"] == "rail"
    assert result["rail_subtype"] == "train"


def test_rail_prediction_needs_structured_evidence() -> None:
    result = resolve_mode(
        {"walk": 0.05, "bike": 0.02, "car": 0.20, "bus": 0.13, "rail": 0.60},
        context={"subway_context_score": 0.55, "subway_line_score": 1.0, "subway_sequence_score": 0.0, "subway_observed_station_count": 1},
    )
    assert result["final_mode"] == "car"
    assert result["decision_status"] == "insufficient_context"


def test_bus_evidence_can_replace_unsupported_rail_prediction() -> None:
    result = resolve_mode(
        {"walk": 0.02, "bike": 0.02, "car": 0.10, "bus": 0.06, "rail": 0.80},
        context={"bus_context_score": 0.45, "subway_context_score": 0.55, "subway_line_score": 1.0, "subway_sequence_score": 0.0, "subway_observed_station_count": 1},
    )
    assert result["final_mode"] == "bus"


def test_non_rail_prediction_requires_strong_rail_confirmation() -> None:
    result = resolve_mode(
        {"walk": 0.10, "bike": 0.05, "car": 0.60, "bus": 0.10, "rail": 0.15},
        context={
            "subway_context_score": 0.55,
            "subway_line_score": 1.0,
            "subway_sequence_score": 1.0,
            "subway_observed_station_count": 3,
        },
    )
    assert result["final_mode"] == "car"
    assert result["decision_status"] == "insufficient_context"
