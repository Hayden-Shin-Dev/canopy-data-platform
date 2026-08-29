from types import SimpleNamespace

from src.integration.segments import smooth_window_modes


def _record(base_mode: str, ml_mode: str, confidence: float, score: float, sequence: float, line: str | None = "5"):
    return {
        "window": SimpleNamespace(predicted_mode=ml_mode, confidence=confidence),
        "decision": {"final_mode": base_mode, "ml_predicted_mode": ml_mode, "ml_confidence": confidence},
        "transit_context": {"matched_subway_line": line, "subway_context_score": score, "subway_sequence_score": sequence},
    }


def test_smoothing_keeps_evidence_backed_rail_run_and_exits_on_walk() -> None:
    records = [
        _record("walk", "walk", 0.9, 0.0, 0.0, None),
        _record("rail", "bike", 0.55, 0.65, 0.5),
        _record("rail", "bike", 0.45, 0.7, 1.0),
        _record("rail", "walk", 0.95, 0.7, 1.0),
    ]
    assert smooth_window_modes(records, minimum_context_score=0.35, minimum_ml_confidence=0.8) == ["walk", "rail", "rail", "walk"]
