from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import replace

from scripts.build_aihub_duration_windows import _join, _normalized_uid
from src.aihub.ingest import AiHubPoint, AiHubTrajectory
from src.aihub.filenames import TmcIdentifier


def _trajectory(name: str, start: datetime, offset: float = 0.0) -> AiHubTrajectory:
    points = tuple(
        AiHubPoint(
            timestamp=start + timedelta(seconds=index),
            latitude=37.5 + offset + index * 0.00001,
            longitude=126.9 + index * 0.00001,
            accuracy_m=5.0,
            altitude_m=10.0,
        )
        for index in range(60)
    )
    return AiHubTrajectory(
        user_id="00000001",
        trajectory_id=name,
        identifier=TmcIdentifier("00000001", name, "part"),
        source_class="CAR",
        canonical_mode="car",
        gps_path=Path(f"{name}.csv"),
        label_path=Path(f"{name}.label.csv"),
        points=points,
        raw_point_count=60,
        missing_coordinate_count=0,
        invalid_coordinate_count=0,
        duplicate_timestamp_count=0,
        backwards_timestamp_count=0,
        gap_count=0,
        label_row_count=60,
        raw_label_values=("2",),
    )


def test_join_recomputes_one_canonical_feature_row_from_raw_points() -> None:
    start = datetime(2024, 1, 1)
    row = _join(_trajectory("left", start), _trajectory("right", start + timedelta(seconds=60)))

    assert row is not None
    assert row["point_count"] == 120
    assert row["observed_duration_sec"] == 119
    assert row["displacement_m"] < row["distance_m"] * 1.01


def test_join_rejects_non_contiguous_raw_trajectories() -> None:
    start = datetime(2024, 1, 1)
    row = _join(_trajectory("left", start), _trajectory("right", start + timedelta(seconds=91)))

    assert row is None


def test_uid_normalization_preserves_manifest_lookup_identity() -> None:
    assert _normalized_uid("00000001") == "1"
    assert _normalized_uid(1) == "1"


def test_join_excludes_trajectory_without_valid_coordinates() -> None:
    start = datetime(2024, 1, 1)
    empty = replace(_trajectory("empty", start), points=tuple())

    assert _join(empty, _trajectory("right", start + timedelta(seconds=60))) is None
