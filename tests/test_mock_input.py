import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOCK_CSV = ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv"
GROUND_TRUTH = ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt"


def test_main_mock_is_canonical_gps_only_input():
    with MOCK_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert rows
    required = {
        "schema_version",
        "trip_id",
        "device_id",
        "sequence",
        "timestamp",
        "latitude",
        "longitude",
        "horizontal_accuracy_m",
        "altitude_m",
        "vertical_accuracy_m",
        "speed_mps",
        "course_deg",
    }
    assert required <= set(reader.fieldnames or [])
    forbidden = {"mode", "transport_mode", "ground_truth", "ground_truth_mode", "segment", "ground_truth_segment", "expected_mode", "label", "target"}
    assert not forbidden.intersection(reader.fieldnames or [])
    assert all(row["trip_id"] == rows[0]["trip_id"] for row in rows)
    assert [int(row["sequence"]) for row in rows] == list(range(len(rows)))


def test_ground_truth_is_separate_evaluation_metadata():
    assert GROUND_TRUTH.is_file()
    assert "DO NOT FEED THIS FILE TO THE MODEL" in GROUND_TRUTH.read_text(encoding="utf-8")
