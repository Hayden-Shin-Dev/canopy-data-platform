"""Build labelled car windows from AI-Hub linked vehicle ZIP archives."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, UTC
import io
from pathlib import Path
import zipfile

import pandas as pd

from src.geolife.raw import TrajectoryPoint
from src.geolife.window_features import compute_window_features
from src.geolife.windows import iter_time_windows
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def _split_for_user(user_id: str) -> str:
    """Use a stable hash bucket so linked users never share a split."""

    bucket = int(user_id[-4:], 16) % 100 if user_id[-4:].isalnum() else sum(map(ord, user_id)) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def _read_points(archive: zipfile.ZipFile, entry: zipfile.ZipInfo) -> list[TrajectoryPoint] | None:
    with archive.open(entry) as stream:
        text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.DictReader(text)
        required = {"timestamp", "latitude", "longitude"}
        if not required <= set(reader.fieldnames or ()):
            return None
        points: list[TrajectoryPoint] = []
        user_id = Path(entry.filename).name.split("-")[1]
        trajectory_id = Path(entry.filename).stem
        for row in reader:
            try:
                timestamp = datetime.fromtimestamp(int(row["timestamp"]) / 1000, tz=UTC).replace(tzinfo=None)
                latitude = float(row["latitude"])
                longitude = float(row["longitude"])
            except (TypeError, ValueError, OverflowError, OSError):
                continue
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                continue
            points.append(TrajectoryPoint(user_id, trajectory_id, latitude, longitude, 0.0, timestamp))
    return points


def _feature_row(window) -> dict[str, object]:
    features = dict(compute_window_features(window.points))
    features.update(
        {
            "accuracy_mean_m": 0.0,
            "accuracy_std_m": 0.0,
            "accuracy_missing_ratio": 1.0,
            "altitude_missing_ratio": 1.0,
            "valid_point_ratio": 1.0,
        }
    )
    return {
        "user_id": window.user_id,
        "trajectory_id": window.trajectory_id,
        "source_class": "LINKED_VEHICLE",
        "canonical_mode": "car",
        "window_start": window.window_start.isoformat(sep=" "),
        "window_end": window.window_end.isoformat(sep=" "),
        "split": _split_for_user(window.user_id),
        **{column: features[column] for column in AIHUB_FEATURE_COLUMNS},
    }


def build(archives: list[str | Path], output_csv: str | Path, *, max_files: int | None = None, window_seconds: int = 120) -> int:
    rows: list[dict[str, object]] = []
    remaining = max_files
    for archive_path in archives:
        with zipfile.ZipFile(archive_path) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            if remaining is not None:
                entries = entries[:remaining]
            for entry in entries:
                points = _read_points(archive, entry)
                if points is None:
                    continue
                for window in iter_time_windows(points, window_seconds=window_seconds, min_points=2):
                    rows.append(_feature_row(window))
            if remaining is not None:
                remaining = max(0, remaining - len(entries))
                if remaining == 0:
                    break
    columns = ["user_id", "trajectory_id", "source_class", "canonical_mode", "window_start", "window_end", "split", *AIHUB_FEATURE_COLUMNS]
    frame = pd.DataFrame(rows, columns=columns)
    destination = Path(output_csv)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8-sig")
    return len(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--window-seconds", type=int, default=120)
    args = parser.parse_args()
    print(build(args.archives, args.output_csv, max_files=args.max_files, window_seconds=args.window_seconds))


if __name__ == "__main__":
    main()
