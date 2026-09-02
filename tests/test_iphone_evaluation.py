import csv
from pathlib import Path

from src.aihub.iphone_evaluation import append_prediction, evaluate_iphone_journey


def _record(timestamp: str, mode: str | None) -> dict[str, object]:
    return {
        "schema_version": "1.0", "journey_id": "journey-1", "model_version": "v3", "git_sha": "1234567",
        "timestamp": timestamp, "latitude": 37.5, "longitude": 126.9, "horizontal_accuracy_m": None,
        "altitude_m": None, "movement_probabilities": {"walk": 0.2, "bike": 0.2, "car": 0.2, "bus": 0.2, "rail": 0.2},
        "movement_prediction": mode, "temporal_prediction": mode, "transit_applicability": "NOT_APPLICABLE",
        "transit_evidence": {}, "final_prediction": mode,
    }


def test_local_iphone_evaluator_reports_sequence_latency_and_coverage(tmp_path: Path) -> None:
    prediction_path = tmp_path / "predictions.jsonl"
    append_prediction(prediction_path, _record("2026-01-01T00:00:00+00:00", None))
    append_prediction(prediction_path, _record("2026-01-01T00:00:10+00:00", "walk"))
    append_prediction(prediction_path, _record("2026-01-01T00:01:05+00:00", "rail"))
    gt_path = tmp_path / "segments.csv"
    with gt_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["segment_start", "segment_end", "true_mode"])
        writer.writeheader()
        writer.writerow({"segment_start": "2026-01-01T00:00:00+00:00", "segment_end": "2026-01-01T00:01:00+00:00", "true_mode": "walk"})
        writer.writerow({"segment_start": "2026-01-01T00:01:00+00:00", "segment_end": "2026-01-01T00:02:00+00:00", "true_mode": "rail"})

    result = evaluate_iphone_journey(prediction_path, gt_path, tmp_path / "result.json")

    assert result["accuracy"] == 1
    assert result["true_sequence"] == ["walk", "rail"]
    assert result["predicted_sequence"] == ["walk", "rail"]
    assert result["transition_latency"][0]["latency_seconds"] == 5
    assert result["prediction_coverage"] == 2 / 3
