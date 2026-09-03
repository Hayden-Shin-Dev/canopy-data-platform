import csv
from pathlib import Path

from datetime import timezone

from src.aihub.features import AIHUB_FEATURE_COLUMNS, compute_aihub_features, feature_row
from src.aihub.runtime import event_features
from src.aihub.ingest import read_trajectory
from src.integration.gps_contract import GpsEvent


def _pair(tmp_path: Path) -> tuple[Path, Path]:
    gps = tmp_path / "TMC-GPS-00000001-a-b-Dataset.csv"
    label = tmp_path / "TMC-LABEL-00000001-a-b-Label.csv"
    with gps.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "accuracy", "latitude", "longitude", "altitude"])
        writer.writerow(["1000", "5", "37.5", "126.9", "10"])
        writer.writerow(["2000", "7", "37.5001", "126.9001", "11"])
    with label.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "label", "detail_label"])
        writer.writerow(["1000", "2", "5"])
        writer.writerow(["2000", "2", "5"])
    return gps, label


def test_features_reuse_existing_step_definitions(tmp_path: Path) -> None:
    gps, label = _pair(tmp_path)
    row = feature_row(read_trajectory("CAR", gps, label))
    assert set(AIHUB_FEATURE_COLUMNS) <= row.keys()
    assert row["canonical_mode"] == "car"
    assert row["valid_point_ratio"] == 1.0
    assert row["accuracy_mean_m"] == 6.0


def test_training_and_runtime_use_identical_canonical_features(tmp_path: Path) -> None:
    gps, label = _pair(tmp_path)
    trajectory = read_trajectory("CAR", gps, label)
    events = [
        GpsEvent(
            schema_version="1.0",
            trip_id=trajectory.trajectory_id,
            device_id=trajectory.user_id,
            sequence=index,
            timestamp=point.timestamp.replace(tzinfo=timezone.utc),
            latitude=point.latitude,
            longitude=point.longitude,
            horizontal_accuracy_m=point.accuracy_m,
            altitude_m=point.altitude_m,
            vertical_accuracy_m=None,
            speed_mps=None,
            course_deg=None,
        )
        for index, point in enumerate(trajectory.points)
    ]

    assert event_features(events) == compute_aihub_features(trajectory)
