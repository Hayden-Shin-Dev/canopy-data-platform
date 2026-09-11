"""Distance calculations for accepted GPS events."""

from __future__ import annotations

from collections.abc import Iterable
from math import asin, cos, radians, sin, sqrt

from .gps_contract import GpsEvent


EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """Return WGS84 coordinate distance using the spherical haversine formula."""

    lat_delta = radians(latitude_b - latitude_a)
    lon_delta = radians(longitude_b - longitude_a)
    a = sin(lat_delta / 2) ** 2 + cos(radians(latitude_a)) * cos(radians(latitude_b)) * sin(lon_delta / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, max(0.0, a))))


def trajectory_distance_km(events: Iterable[GpsEvent]) -> float:
    """Sum consecutive accepted event distances in timestamp/sequence order."""

    ordered = list(events)
    return sum(
        haversine_distance_km(previous.latitude, previous.longitude, current.latitude, current.longitude)
        for previous, current in zip(ordered, ordered[1:])
    )
