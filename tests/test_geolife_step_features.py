from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.geolife.raw import TrajectoryPoint
from src.geolife.step_features import compute_step_features


def make_point(seconds: int, latitude: float = 39.0, longitude: float = 116.0) -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id="000",
        trajectory_id="sample",
        latitude=latitude,
        longitude=longitude,
        altitude_ft=0.0,
        timestamp=datetime(2020, 1, 1) + timedelta(seconds=seconds),
    )


class GeoLifeStepFeatureTests(unittest.TestCase):
    def test_stationary_step_is_stop(self) -> None:
        result = compute_step_features(make_point(0), make_point(5))
        self.assertEqual(result.time_delta_sec, 5.0)
        self.assertEqual(result.distance_delta_m, 0.0)
        self.assertEqual(result.speed_mps, 0.0)
        self.assertTrue(result.stop_flag)
        self.assertFalse(result.gap_step)

    def test_positive_step_has_speed_and_bearing(self) -> None:
        result = compute_step_features(
            make_point(0),
            make_point(5, latitude=39.001),
        )
        self.assertGreater(result.distance_delta_m, 0.0)
        self.assertGreater(result.speed_mps or 0.0, 0.0)
        self.assertIsNotNone(result.bearing_deg)

    def test_zero_time_delta_is_not_a_valid_speed_step(self) -> None:
        result = compute_step_features(make_point(0), make_point(0, latitude=39.001))
        self.assertIsNone(result.speed_mps)
        self.assertIsNone(result.stop_flag)
        self.assertFalse(result.gap_step)

    def test_long_gap_is_excluded_from_speed_statistics(self) -> None:
        result = compute_step_features(make_point(0), make_point(121, latitude=39.001))
        self.assertTrue(result.gap_step)
        self.assertIsNone(result.speed_mps)

    def test_acceleration_uses_previous_speed(self) -> None:
        result = compute_step_features(
            make_point(0),
            make_point(5, latitude=39.001),
            previous_speed_mps=1.0,
        )
        self.assertIsNotNone(result.acceleration_mps2)


if __name__ == "__main__":
    unittest.main()
