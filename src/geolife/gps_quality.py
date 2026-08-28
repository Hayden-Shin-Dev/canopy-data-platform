"""mode와 무관한 GeoLife GPS step 품질 필터."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Iterator

from src.common.geo import haversine_distance_km
from src.geolife.config import DEFAULT_MAX_ALTITUDE_JUMP_M, DEFAULT_MAX_PLAUSIBLE_SPEED_MPS, DEFAULT_GAP_THRESHOLD_SECONDS
from src.geolife.raw import TrajectoryPoint


@dataclass(frozen=True)
class GpsQualityPolicy:
    max_speed_mps: float = DEFAULT_MAX_PLAUSIBLE_SPEED_MPS
    max_gap_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS
    max_altitude_jump_m: float = DEFAULT_MAX_ALTITUDE_JUMP_M
    drop_duplicate_points: bool = True

    def __post_init__(self) -> None:
        if self.max_speed_mps <= 0 or self.max_gap_seconds <= 0 or self.max_altitude_jump_m <= 0:
            raise ValueError("GPS quality threshold는 양수여야 합니다")


@dataclass
class GpsQualityStats:
    points_in: int = 0
    points_out: int = 0
    dropped_invalid_value: int = 0
    dropped_duplicate: int = 0
    segment_break_nonpositive_dt: int = 0
    segment_break_long_gap: int = 0
    segment_break_speed: int = 0
    segment_break_altitude: int = 0

    @property
    def segment_break_count(self) -> int:
        return (
            self.segment_break_nonpositive_dt
            + self.segment_break_long_gap
            + self.segment_break_speed
            + self.segment_break_altitude
        )


def _with_segment_id(point: TrajectoryPoint, segment_index: int) -> TrajectoryPoint:
    if segment_index == 0:
        return point
    return TrajectoryPoint(
        user_id=point.user_id,
        trajectory_id=f"{point.trajectory_id}#q{segment_index}",
        latitude=point.latitude,
        longitude=point.longitude,
        altitude_ft=point.altitude_ft,
        timestamp=point.timestamp,
    )


def iter_quality_points(
    points: Iterable[TrajectoryPoint],
    *,
    policy: GpsQualityPolicy = GpsQualityPolicy(),
    stats: GpsQualityStats | None = None,
) -> Iterator[TrajectoryPoint]:
    """나쁜 step에서 trajectory를 분리하고 유효 point를 반환한다."""
    quality_stats = stats or GpsQualityStats()
    previous: TrajectoryPoint | None = None
    current_key: tuple[str, str] | None = None
    segment_index = 0

    for point in points:
        quality_stats.points_in += 1
        key = (point.user_id, point.trajectory_id)
        values = (point.latitude, point.longitude, point.altitude_ft)
        if not all(math.isfinite(value) for value in values):
            quality_stats.dropped_invalid_value += 1
            continue
        if key != current_key:
            current_key = key
            previous = None
            segment_index = 0
        if previous is None:
            previous = point
            quality_stats.points_out += 1
            yield _with_segment_id(point, segment_index)
            continue

        delta_seconds = (point.timestamp - previous.timestamp).total_seconds()
        if delta_seconds <= 0:
            same_position = point.latitude == previous.latitude and point.longitude == previous.longitude
            if policy.drop_duplicate_points and delta_seconds == 0 and same_position:
                quality_stats.dropped_duplicate += 1
                continue
            quality_stats.segment_break_nonpositive_dt += 1
            segment_index += 1
            previous = point
            quality_stats.points_out += 1
            yield _with_segment_id(point, segment_index)
            continue
        if delta_seconds > policy.max_gap_seconds:
            quality_stats.segment_break_long_gap += 1
            segment_index += 1
            previous = point
            quality_stats.points_out += 1
            yield _with_segment_id(point, segment_index)
            continue

        distance_m = haversine_distance_km(
            previous.latitude, previous.longitude, point.latitude, point.longitude
        ) * 1000
        if distance_m / delta_seconds > policy.max_speed_mps:
            quality_stats.segment_break_speed += 1
            segment_index += 1
            previous = point
            quality_stats.points_out += 1
            yield _with_segment_id(point, segment_index)
            continue

        altitude_delta_m = abs(point.altitude_ft - previous.altitude_ft) * 0.3048
        if altitude_delta_m > policy.max_altitude_jump_m:
            quality_stats.segment_break_altitude += 1
            segment_index += 1
            previous = point
            quality_stats.points_out += 1
            yield _with_segment_id(point, segment_index)
            continue

        previous = point
        quality_stats.points_out += 1
        yield _with_segment_id(point, segment_index)
