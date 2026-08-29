from pathlib import Path

from scripts.evaluate_mock_trip import evaluate, read_ground_truth_modes


ROOT = Path(__file__).resolve().parents[1]


def test_ground_truth_parser_is_evaluation_only():
    assert read_ground_truth_modes(ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt") == ("walk", "rail", "walk")


def test_mock_evaluation_runs_production_pipeline_without_labels():
    report = evaluate()

    assert report["input"]["rows"] == 433
    assert report["input"]["ground_truth_used_by_inference"] is False
    assert report["production_pipeline"]["status"] == "PASS"
    assert report["label_leakage"]["status"] == "PASS"
