from __future__ import annotations

import pytest

from src.common.geo import haversine_distance_km


def test_haversine_distance_is_zero_for_same_point() -> None:
    assert haversine_distance_km(37.5665, 126.9780, 37.5665, 126.9780) == pytest.approx(0)


def test_haversine_distance_matches_known_equator_distance() -> None:
    assert haversine_distance_km(0, 0, 0, 1) == pytest.approx(111.195, rel=1e-4)


def test_haversine_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValueError, match="위도"):
        haversine_distance_km(91, 0, 0, 0)
