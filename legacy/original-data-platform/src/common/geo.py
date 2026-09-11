"""좌표가 있을 때 재사용하는 지리 계산 함수."""

from __future__ import annotations

import math


EARTH_RADIUS_KM = 6371.0088


def _validate_coordinate(latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("위도와 경도는 유한한 숫자여야 합니다")
    if not -90 <= latitude <= 90:
        raise ValueError("위도는 -90에서 90 사이여야 합니다")
    if not -180 <= longitude <= 180:
        raise ValueError("경도는 -180에서 180 사이여야 합니다")


def haversine_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """두 WGS84 좌표의 대권거리를 km 단위로 계산한다."""

    values = (latitude_1, longitude_1, latitude_2, longitude_2)
    if not all(isinstance(value, (int, float)) for value in values):
        raise TypeError("좌표는 숫자여야 합니다")
    _validate_coordinate(float(latitude_1), float(longitude_1))
    _validate_coordinate(float(latitude_2), float(longitude_2))
    lat1, lat2 = math.radians(latitude_1), math.radians(latitude_2)
    delta_lat = math.radians(latitude_2 - latitude_1)
    delta_lon = math.radians(longitude_2 - longitude_1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
