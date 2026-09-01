import csv
from pathlib import Path

import pytest

from src.aihub.ingest import AiHubFormatError, profile_split, read_trajectory


def _write_pair(root: Path, *, label_timestamp: str = "1000") -> tuple[Path, Path]:
    raw = root / "TMC-GPS-00000001-a-b-Dataset.csv"
    label = root / "TMC-LABEL-00000001-a-b-Label.csv"
    with raw.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "accuracy", "latitude", "longitude", "altitude"])
        writer.writerow(["1000", "4.0", "37.5", "126.9", "12"])
        writer.writerow(["2000", "", "", "", ""])
    with label.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "label", "detail_label"])
        writer.writerow([label_timestamp, "2", "5"])
        writer.writerow(["2000", "2", "5"])
    return raw, label


def test_reads_coordinates_and_records_missing_rows(tmp_path: Path) -> None:
    raw, label = _write_pair(tmp_path)
    trajectory = read_trajectory("CAR", raw, label)
    assert trajectory.canonical_mode == "car"
    assert trajectory.raw_point_count == 2
    assert len(trajectory.points) == 1
    assert trajectory.missing_coordinate_count == 1
    assert trajectory.raw_label_values == ("2",)


def test_rejects_label_timestamp_mismatch(tmp_path: Path) -> None:
    raw, label = _write_pair(tmp_path, label_timestamp="999")
    with pytest.raises(AiHubFormatError, match="timestamp mismatch"):
        read_trajectory("CAR", raw, label)


def test_profile_split_is_streaming_and_class_aware(tmp_path: Path) -> None:
    raw_base = tmp_path / "Training" / "01.raw"
    label_base = tmp_path / "Training" / "02.labels"
    for source_class in ("WALK", "BIKE", "CAR", "BUS", "SUBWAY"):
        (raw_base / f"TS_GPS_{source_class}").mkdir(parents=True)
        (label_base / f"TL_GPS_{source_class}").mkdir(parents=True)
    raw_root = raw_base / "TS_GPS_CAR"
    label_root = label_base / "TL_GPS_CAR"
    raw, label = _write_pair(raw_root)
    label.rename(label_root / label.name)
    result = profile_split(tmp_path, "Training")
    assert result.trajectory_count == 1
    assert result.by_class["car"]["valid_point_count"] == 1
