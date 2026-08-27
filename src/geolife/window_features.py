"""Trajectory point 묶음에서 Window 수준 Feature를 만든다."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from src.geolife.config import DEFAULT_GAP_THRESHOLD_SECONDS, DEFAULT_STOP_THRESHOLD_MPS
from src.geolife.raw import TrajectoryPoint
from src.geolife.step_features import compute_step_features


def _std(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def compute_window_features(
    points: Sequence[TrajectoryPoint],
    *,
    gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
    stop_threshold_mps: float = DEFAULT_STOP_THRESHOLD_MPS,
) -> dict[str, float | int]:
    """한 Window의 수치 Feature를 계산한다.

    distance와 sampling interval은 양의 시간 차이가 gap 기준 이하인 step만 합산한다.
    긴 gap은 `gap_step_count`로만 세고 속도·가속도 통계에는 넣지 않는다.
    """
    if len(points) < 2:
        raise ValueError("Window에는 최소 2개의 point가 필요합니다")

    distances: list[float] = []
    intervals: list[float] = []
    speeds: list[float] = []
    accelerations: list[float] = []
    heading_changes: list[float] = []
    stop_flags: list[bool] = []
    gap_step_count = 0
    previous_speed = None
    previous_bearing = None

    for start, end in zip(points, points[1:]):
        step = compute_step_features(
            start,
            end,
            previous_speed_mps=previous_speed,
            previous_bearing_deg=previous_bearing,
            gap_threshold_seconds=gap_threshold_seconds,
            stop_threshold_mps=stop_threshold_mps,
        )
        if step.gap_step:
            gap_step_count += 1
            previous_speed = None
            previous_bearing = None
            continue
        if step.speed_mps is None:
            previous_speed = None
            previous_bearing = None
            continue
        distances.append(step.distance_delta_m)
        intervals.append(step.time_delta_sec)
        speeds.append(step.speed_mps)
        stop_flags.append(bool(step.stop_flag))
        if step.acceleration_mps2 is not None:
            accelerations.append(step.acceleration_mps2)
        if step.bearing_change_deg is not None:
            heading_changes.append(step.bearing_change_deg)
        previous_speed = step.speed_mps
        previous_bearing = step.bearing_deg

    displacement_m = compute_step_features(points[0], points[-1], gap_threshold_seconds=float("inf")).distance_delta_m
    altitude_values = [point.altitude_ft * 0.3048 for point in points]
    observed_duration_sec = (points[-1].timestamp - points[0].timestamp).total_seconds()
    distance_m = sum(distances)

    return {
        "point_count": len(points),
        "observed_duration_sec": observed_duration_sec,
        "distance_m": distance_m,
        "displacement_m": displacement_m,
        "straightness_ratio": displacement_m / distance_m if distance_m else 0.0,
        "mean_speed_mps": statistics.mean(speeds) if speeds else 0.0,
        "max_speed_mps": max(speeds, default=0.0),
        "speed_std_mps": _std(speeds),
        "mean_abs_acceleration_mps2": statistics.mean(abs(value) for value in accelerations) if accelerations else 0.0,
        "acceleration_std_mps2": _std(accelerations),
        "stop_ratio": statistics.mean(stop_flags) if stop_flags else 0.0,
        "mean_heading_change_deg": statistics.mean(heading_changes) if heading_changes else 0.0,
        "altitude_range_m": max(altitude_values) - min(altitude_values),
        "avg_sampling_interval_sec": statistics.mean(intervals) if intervals else 0.0,
        "valid_step_count": len(speeds),
        "gap_step_count": gap_step_count,
    }

