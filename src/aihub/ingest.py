"""Streaming readers and quality counters for the AI-Hub TMC dataset."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from .config import AIHUB_TO_CANOPY, GPS_HEADER, LABEL_HEADER
from .filenames import TmcIdentifier, label_filename, parse_tmc_filename


class AiHubFormatError(ValueError):
    """Raised when an AI-Hub file does not follow the observed schema."""


@dataclass(frozen=True)
class AiHubPoint:
    timestamp: datetime
    latitude: float
    longitude: float
    accuracy_m: float | None
    altitude_m: float | None


@dataclass(frozen=True)
class AiHubTrajectory:
    user_id: str
    trajectory_id: str
    identifier: TmcIdentifier
    source_class: str
    canonical_mode: str
    gps_path: Path
    label_path: Path
    points: tuple[AiHubPoint, ...]
    raw_point_count: int
    missing_coordinate_count: int
    invalid_coordinate_count: int
    duplicate_timestamp_count: int
    backwards_timestamp_count: int
    gap_count: int
    label_row_count: int
    raw_label_values: tuple[str, ...]


@dataclass
class QualityProfile:
    """Streaming counters; no complete dataset is held in memory."""

    trajectory_count: int = 0
    raw_point_count: int = 0
    valid_point_count: int = 0
    missing_coordinate_count: int = 0
    invalid_coordinate_count: int = 0
    duplicate_timestamp_count: int = 0
    backwards_timestamp_count: int = 0
    gap_count: int = 0
    label_row_count: int = 0
    label_timestamp_mismatch_count: int = 0
    by_class: dict[str, dict[str, int]] = field(default_factory=dict)
    by_gap_seconds: Counter[str] = field(default_factory=Counter)

    def add(self, trajectory: AiHubTrajectory, *, gap_threshold_seconds: float) -> None:
        self.trajectory_count += 1
        self.raw_point_count += trajectory.raw_point_count
        self.valid_point_count += len(trajectory.points)
        self.missing_coordinate_count += trajectory.missing_coordinate_count
        self.invalid_coordinate_count += trajectory.invalid_coordinate_count
        self.duplicate_timestamp_count += trajectory.duplicate_timestamp_count
        self.backwards_timestamp_count += trajectory.backwards_timestamp_count
        self.gap_count += trajectory.gap_count
        self.label_row_count += trajectory.label_row_count
        bucket = self.by_class.setdefault(
            trajectory.canonical_mode,
            {"trajectory_count": 0, "raw_point_count": 0, "valid_point_count": 0},
        )
        bucket["trajectory_count"] += 1
        bucket["raw_point_count"] += trajectory.raw_point_count
        bucket["valid_point_count"] += len(trajectory.points)
        for left, right in zip(trajectory.points, trajectory.points[1:]):
            gap = (right.timestamp - left.timestamp).total_seconds()
            if gap > gap_threshold_seconds:
                self.by_gap_seconds["over_threshold"] += 1
            elif gap > 0:
                self.by_gap_seconds[str(int(gap))] += 1

    def as_dict(self) -> dict[str, object]:
        return {
            "trajectory_count": self.trajectory_count,
            "raw_point_count": self.raw_point_count,
            "valid_point_count": self.valid_point_count,
            "missing_coordinate_count": self.missing_coordinate_count,
            "invalid_coordinate_count": self.invalid_coordinate_count,
            "duplicate_timestamp_count": self.duplicate_timestamp_count,
            "backwards_timestamp_count": self.backwards_timestamp_count,
            "gap_count": self.gap_count,
            "label_row_count": self.label_row_count,
            "label_timestamp_mismatch_count": self.label_timestamp_mismatch_count,
            "by_class": {key: value for key, value in sorted(self.by_class.items())},
            "gap_seconds": dict(sorted(self.by_gap_seconds.items())),
        }


def _class_directories(root: Path, split: str) -> Iterator[tuple[str, Path, Path]]:
    split_root = root / split
    raw_candidates = sorted(path for path in split_root.iterdir() if path.is_dir() and path.name.startswith("01."))
    label_candidates = sorted(path for path in split_root.iterdir() if path.is_dir() and path.name.startswith("02."))
    if len(raw_candidates) != 1 or len(label_candidates) != 1:
        raise FileNotFoundError(f"AI-Hub split directories not found below: {split_root}")
    raw_root = raw_candidates[0]
    label_root = label_candidates[0]
    for source_class, canonical_mode in AIHUB_TO_CANOPY.items():
        raw_candidates = sorted(path for path in raw_root.iterdir() if source_class in path.name and path.is_dir())
        label_candidates = sorted(path for path in label_root.iterdir() if source_class in path.name and path.is_dir())
        if len(raw_candidates) != 1 or len(label_candidates) != 1:
            raise AiHubFormatError(f"Expected one raw and label directory for {source_class}")
        yield source_class, raw_candidates[0], label_candidates[0]


def iter_gps_files(root: str | Path, split: str = "Training") -> Iterator[tuple[str, Path, Path]]:
    """Yield class and paired GPS/Label paths without reading file contents."""

    for source_class, raw_dir, label_dir in _class_directories(Path(root), split):
        for gps_path in sorted(raw_dir.rglob("TMC-GPS-*.csv")):
            expected_label = label_dir / label_filename(gps_path)
            if not expected_label.is_file():
                raise AiHubFormatError(f"Label file is missing for {gps_path.name}")
            yield source_class, gps_path, expected_label


def _parse_timestamp(raw: str, path: Path, row_number: int) -> datetime:
    try:
        millis = int(raw)
        return datetime.fromtimestamp(millis / 1000, tz=UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError) as error:
        raise AiHubFormatError(f"Invalid millisecond timestamp at {path}:{row_number}") from error


def _optional_float(raw: str, path: Path, row_number: int) -> float | None:
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError as error:
        raise AiHubFormatError(f"Invalid numeric value at {path}:{row_number}") from error


def read_trajectory(
    source_class: str,
    gps_path: str | Path,
    label_path: str | Path,
    *,
    strict_label_timestamps: bool = True,
    read_label_content: bool = True,
) -> AiHubTrajectory:
    """Read one 60-point TMC file pair; only that pair is held in memory."""

    gps_path = Path(gps_path)
    label_path = Path(label_path)
    identifier = parse_tmc_filename(gps_path)
    canonical_mode = AIHUB_TO_CANOPY.get(source_class)
    if canonical_mode is None:
        raise AiHubFormatError(f"Unknown AI-Hub source class: {source_class}")

    with gps_path.open("r", encoding="utf-8-sig", newline="") as gps_stream:
        gps_reader = csv.DictReader(gps_stream)
        if tuple(gps_reader.fieldnames or ()) != GPS_HEADER:
            raise AiHubFormatError(f"Unexpected GPS header at {gps_path}")
        rows = list(gps_reader)

    if read_label_content:
        with label_path.open("r", encoding="utf-8-sig", newline="") as label_stream:
            label_reader = csv.DictReader(label_stream)
            if tuple(label_reader.fieldnames or ()) != LABEL_HEADER:
                raise AiHubFormatError(f"Unexpected Label header at {label_path}")
            label_rows = list(label_reader)
    else:
        label_rows = []

    if read_label_content and len(rows) != len(label_rows):
        raise AiHubFormatError(
            f"GPS/Label row count mismatch for {gps_path.name}: {len(rows)} != {len(label_rows)}"
        )

    points: list[AiHubPoint] = []
    missing_coordinates = 0
    invalid_coordinates = 0
    duplicate_timestamps = 0
    backwards_timestamps = 0
    gap_count = 0
    label_timestamp_mismatches = 0
    previous_timestamp: datetime | None = None
    raw_label_values: set[str] = set()

    label_iter = iter(label_rows)
    for row_number, row in enumerate(rows, start=2):
        timestamp = _parse_timestamp(row["timestamp"], gps_path, row_number)
        if read_label_content:
            label_row = next(label_iter)
            label_timestamp = _parse_timestamp(label_row["timestamp"], label_path, row_number)
            if timestamp != label_timestamp:
                label_timestamp_mismatches += 1
            raw_label_values.add(label_row["label"].strip())
        if previous_timestamp is not None:
            delta = (timestamp - previous_timestamp).total_seconds()
            if delta == 0:
                duplicate_timestamps += 1
            elif delta < 0:
                backwards_timestamps += 1
            elif delta > 120:
                gap_count += 1
        previous_timestamp = timestamp

        raw_latitude = row["latitude"].strip()
        raw_longitude = row["longitude"].strip()
        if not raw_latitude or not raw_longitude:
            missing_coordinates += 1
            continue
        try:
            latitude = float(raw_latitude)
            longitude = float(raw_longitude)
        except ValueError:
            invalid_coordinates += 1
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            invalid_coordinates += 1
            continue
        points.append(
            AiHubPoint(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                accuracy_m=_optional_float(row["accuracy"], gps_path, row_number),
                altitude_m=_optional_float(row["altitude"], gps_path, row_number),
            )
        )

    if strict_label_timestamps and label_timestamp_mismatches:
        raise AiHubFormatError(f"GPS/Label timestamp mismatch for {gps_path.name}")
    return AiHubTrajectory(
        user_id=identifier.uid,
        trajectory_id=gps_path.stem,
        identifier=identifier,
        source_class=source_class,
        canonical_mode=canonical_mode,
        gps_path=gps_path,
        label_path=label_path,
        points=tuple(points),
        raw_point_count=len(rows),
        missing_coordinate_count=missing_coordinates,
        invalid_coordinate_count=invalid_coordinates,
        duplicate_timestamp_count=duplicate_timestamps,
        backwards_timestamp_count=backwards_timestamps,
        gap_count=gap_count,
        label_row_count=len(label_rows) if read_label_content else len(rows),
        raw_label_values=tuple(sorted(raw_label_values)),
    )


def iter_trajectories(
    root: str | Path,
    split: str = "Training",
    *,
    strict_label_timestamps: bool = True,
    read_label_content: bool = True,
) -> Iterator[AiHubTrajectory]:
    for source_class, gps_path, label_path in iter_gps_files(root, split):
        yield read_trajectory(
            source_class,
            gps_path,
            label_path,
            strict_label_timestamps=strict_label_timestamps,
            read_label_content=read_label_content,
        )


def profile_split(
    root: str | Path,
    split: str = "Training",
    *,
    gap_threshold_seconds: float = 120,
    workers: int = 1,
    read_label_content: bool = True,
) -> QualityProfile:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    profile = QualityProfile()
    files = iter_gps_files(root, split)
    if workers == 1:
        trajectories = (
            read_trajectory(source_class, gps_path, label_path, read_label_content=read_label_content)
            for source_class, gps_path, label_path in files
        )
        for trajectory in trajectories:
            profile.add(trajectory, gap_threshold_seconds=gap_threshold_seconds)
        return profile
    with ThreadPoolExecutor(max_workers=workers) as executor:
        trajectories = executor.map(
            lambda item: read_trajectory(*item, read_label_content=read_label_content),
            files,
            buffersize=max(2, workers * 2),
        )
        for trajectory in trajectories:
            profile.add(trajectory, gap_threshold_seconds=gap_threshold_seconds)
    return profile
