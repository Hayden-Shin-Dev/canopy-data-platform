"""Build Canopy-compatible window features from one AI-Hub trajectory."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.geolife.raw import TrajectoryPoint
from src.geolife.window_features import compute_window_features

from .ingest import AiHubPoint, AiHubTrajectory


AIHUB_FEATURE_COLUMNS = (
    "point_count",
    "observed_duration_sec",
    "distance_m",
    "displacement_m",
    "straightness_ratio",
    "mean_speed_mps",
    "max_speed_mps",
    "speed_std_mps",
    "mean_abs_acceleration_mps2",
    "acceleration_std_mps2",
    "stop_ratio",
    "mean_heading_change_deg",
    "altitude_range_m",
    "avg_sampling_interval_sec",
    "valid_step_count",
    "gap_step_count",
    "accuracy_mean_m",
    "accuracy_std_m",
    "accuracy_missing_ratio",
    "altitude_missing_ratio",
    "valid_point_ratio",
)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def trajectory_points(trajectory: AiHubTrajectory) -> list[TrajectoryPoint]:
    return [
        TrajectoryPoint(
            user_id=trajectory.user_id,
            trajectory_id=trajectory.trajectory_id,
            latitude=point.latitude,
            longitude=point.longitude,
            altitude_ft=(point.altitude_m or 0.0) / 0.3048,
            timestamp=point.timestamp,
        )
        for point in trajectory.points
    ]


def canonical_window_features(
    points: list[AiHubPoint] | tuple[AiHubPoint, ...],
    *,
    user_id: str,
    trajectory_id: str,
    raw_point_count: int | None = None,
) -> dict[str, float | int]:
    """학습과 실시간 추론이 함께 쓰는 단일 GPS Feature 계산 경로."""

    if len(points) < 2:
        raise ValueError("At least two valid GPS points are required")
    canonical_points = [
        TrajectoryPoint(
            user_id=user_id,
            trajectory_id=trajectory_id,
            latitude=point.latitude,
            longitude=point.longitude,
            altitude_ft=(point.altitude_m or 0.0) / 0.3048,
            timestamp=point.timestamp.replace(tzinfo=None),
        )
        for point in points
    ]
    features = dict(compute_window_features(canonical_points))
    accuracy_values = [point.accuracy_m for point in points if point.accuracy_m is not None]
    altitude_missing = sum(point.altitude_m is None for point in points)
    source_count = len(points) if raw_point_count is None else raw_point_count
    features.update(
        {
            "accuracy_mean_m": sum(accuracy_values) / len(accuracy_values) if accuracy_values else 0.0,
            "accuracy_std_m": _std(accuracy_values),
            "accuracy_missing_ratio": 1 - len(accuracy_values) / len(points),
            "altitude_missing_ratio": altitude_missing / len(points),
            "valid_point_ratio": len(points) / source_count if source_count else 0.0,
        }
    )
    return features


def compute_aihub_features(trajectory: AiHubTrajectory) -> dict[str, float | int]:
    """AI-Hub 원본 trajectory를 canonical Feature 계약으로 변환한다."""

    return canonical_window_features(
        trajectory.points,
        user_id=trajectory.user_id,
        trajectory_id=trajectory.trajectory_id,
        raw_point_count=trajectory.raw_point_count,
    )


def feature_row(trajectory: AiHubTrajectory) -> dict[str, object]:
    points = trajectory_points(trajectory)
    if len(points) < 2:
        raise ValueError("At least two valid GPS points are required")
    return {
        "user_id": trajectory.user_id,
        "trajectory_id": trajectory.trajectory_id,
        "source_class": trajectory.source_class,
        "canonical_mode": trajectory.canonical_mode,
        "window_start": points[0].timestamp.isoformat(sep=" "),
        "window_end": points[-1].timestamp.isoformat(sep=" "),
        "raw_point_count": trajectory.raw_point_count,
        "missing_coordinate_count": trajectory.missing_coordinate_count,
        "invalid_coordinate_count": trajectory.invalid_coordinate_count,
        "duplicate_timestamp_count": trajectory.duplicate_timestamp_count,
        "backwards_timestamp_count": trajectory.backwards_timestamp_count,
        "gap_count": trajectory.gap_count,
        "raw_label_values": "|".join(trajectory.raw_label_values),
        **compute_aihub_features(trajectory),
    }
