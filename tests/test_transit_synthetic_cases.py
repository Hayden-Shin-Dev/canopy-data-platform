from src.transit_context.resolver import resolve_mode


def test_bus_route_following_corrects_to_bus() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.65, "bus": 0.15, "rail": 0.10}, context={"bus_context_score": 0.95})
    assert result["final_mode"] == "bus"


def test_near_stop_but_wrong_sequence_does_not_force_bus() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.75, "bus": 0.10, "rail": 0.05}, context={"bus_context_score": 0.25})
    assert result["final_mode"] == "car"


def test_same_line_subway_context_selects_subway_subtype() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.45, "bus": 0.1, "rail": 0.35}, context={"subway_context_score": 0.9})
    assert result["final_mode"] == "rail"
    assert result["rail_subtype"] == "subway"


def test_station_pass_with_weak_context_retains_car() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.85, "bus": 0.03, "rail": 0.02}, context={"subway_context_score": 0.2})
    assert result["final_mode"] == "car"


def test_strong_korail_context_selects_train() -> None:
    result = resolve_mode({"walk": 0.05, "bike": 0.05, "car": 0.2, "bus": 0.1, "rail": 0.6}, context={"train_context_score": 0.9})
    assert result["rail_subtype"] == "train"


def test_insufficient_context_keeps_uncertain_ml_decision() -> None:
    result = resolve_mode({"walk": 0.2, "bike": 0.2, "car": 0.2, "bus": 0.2, "rail": 0.2})
    assert result["decision_status"] == "insufficient_context"
