from pathlib import Path

from src.evaluation.dataset_v1 import discover_dataset, validate_frozen_dataset, validate_gps_schema


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/seoul-synthetic/evaluation_dataset_v3"


def test_v3_manifest_and_file_counts_are_frozen():
    dataset = discover_dataset(DATASET)
    result = validate_frozen_dataset(dataset, verify_hashes=False)
    assert result["status"] == "PASS"
    assert result["dataset_version"] == "evaluation_dataset_v3"
    assert result["journey_count"] == 700


def test_v3_gps_contract_has_no_label_leakage():
    result = validate_gps_schema(DATASET / "gps/trip_000001.csv")
    assert result["status"] == "PASS"
    assert not result["forbidden"]
