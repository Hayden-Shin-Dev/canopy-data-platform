from datetime import datetime, timezone

from scripts.evaluate_dataset_v1 import _compress, _label_at, _metric_payload, _trip_prediction


def test_mode_sequence_helpers():
    assert _compress(["walk", "walk", "rail", "rail", "walk"]) == ["walk", "rail", "walk"]
    assert _trip_prediction(["walk", "bike", "walk"], True) == "walk|bike|walk"
    assert _trip_prediction(["walk", "bike", "bike"], False) == "bike"


def test_ground_truth_interval_labeling():
    segments = [{"start": datetime(2026, 1, 1, tzinfo=timezone.utc), "end": datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc), "mode": "walk"}]
    assert _label_at(datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc), segments) == "walk"
    assert _label_at(datetime(2026, 1, 1, 0, 3, tzinfo=timezone.utc), segments) is None


def test_metrics_keep_all_five_classes():
    result = _metric_payload(["walk", "bike", "car", "bus", "rail"], ["walk", "car", "car", "bus", "rail"])
    assert result["count"] == 5
    assert set(result["per_class"]) == {"walk", "bike", "car", "bus", "rail"}
    assert result["per_class"]["bike"]["support"] == 1
