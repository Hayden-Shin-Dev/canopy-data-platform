from pathlib import Path

from src.evaluation.dataset_v1 import discover_dataset, validate_frozen_dataset, validate_gps_schema


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation"


def test_discovers_single_frozen_dataset():
    dataset = discover_dataset(DATASET)
    assert dataset.root.name == "evaluation_dataset_v1"
    assert len(dataset.gps_files) == 700
    assert len(dataset.ground_truth_files) == 700


def test_validates_manifests_and_hashes():
    dataset = discover_dataset(DATASET)
    result = validate_frozen_dataset(dataset)
    assert result["status"] == "PASS"
    assert result["hashes_checked"] == 1400
    assert result["hashes_passed"] == 1400
    assert len(result["hashes_missing_optional"]) == 30


def test_gps_schema_has_no_label_leakage():
    dataset = discover_dataset(DATASET)
    result = validate_gps_schema(dataset.gps_files[0])
    assert result["status"] == "PASS"
    assert result["forbidden"] == []
