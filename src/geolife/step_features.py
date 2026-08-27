"""인접한 GeoLife GPS point 사이의 이동 Feature를 계산한다."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.common.geo import haversine_distance_km
from src.geolife.raw import TrajectoryPoint


@dataclass(frozen=True)
class StepFeatures:
    time_delta_sec: float
    distance_delta_m: float
    speed_mps: float | None
    acceleration_mps2: float | None
    bearing_deg: float | None
    bearing_change_deg: float | None
    stop_flag: bool | None
    gap_step: bool


def _bearing_deg(start: TrajectoryPoint, end: TrajectoryPoint) -> float:
    lat1 = math.radians(start.latitude)
    lat2 = math.radians(end.latitude)
    delta_lon = math.radians(end.longitude - start.longitude)
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _heading_change(previous: float, current: float) -> float:
    return abs((current - previous + 180) % 360 - 180)


def compute_step_features(
    start: TrajectoryPoint,
    end: TrajectoryPoint,
    *,
    previous_speed_mps: float | None = None,
    previous_bearing_deg: float | None = None,
    gap_threshold_seconds: float = 120,
    stop_threshold_mps: float = 0.5,
) -> StepFeatures:
    """한 step을 계산한다. 긴 gap과 유효하지 않은 시간 차이는 속도 통계에서 제외한다."""
    time_delta_sec = (end.timestamp - start.timestamp).total_seconds()
    distance_delta_m = haversine_distance_km(
        start.latitude,
        start.longitude,
        end.latitude,
        end.longitude,
    ) * 1000
    gap_step = time_delta_sec > gap_threshold_seconds
    if time_delta_sec <= 0 or gap_step:
        return StepFeatures(
            time_delta_sec=time_delta_sec,
            distance_delta_m=distance_delta_m,
            speed_mps=None,
            acceleration_mps2=None,
            bearing_deg=None,
            bearing_change_deg=None,
            stop_flag=None,
            gap_step=gap_step,
        )

    speed_mps = distance_delta_m / time_delta_sec
    acceleration_mps2 = (
        (speed_mps - previous_speed_mps) / time_delta_sec
        if previous_speed_mps is not None
        else None
    )
    bearing_deg = _bearing_deg(start, end)
    bearing_change_deg = (
        _heading_change(previous_bearing_deg, bearing_deg)
        if previous_bearing_deg is not None
        else None
    )
    return StepFeatures(
        time_delta_sec=time_delta_sec,
        distance_delta_m=distance_delta_m,
        speed_mps=speed_mps,
        acceleration_mps2=acceleration_mps2,
        bearing_deg=bearing_deg,
        bearing_change_deg=bearing_change_deg,
        stop_flag=speed_mps <= stop_threshold_mps,
        gap_step=False,
    )

