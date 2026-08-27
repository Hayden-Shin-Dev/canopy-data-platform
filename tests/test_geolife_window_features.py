from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.geolife.raw import TrajectoryPoint
from src.geolife.window_features import compute_window_features


def make_point(seconds: int, latitude: float = 39.0) -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id="000",
        trajectory_id="sample",
        latitude=latitude,
        longitude=116.0,
        altitude_ft=100.0 + seconds,
        timestamp=datetime(2020, 1, 1) + timedelta(seconds=seconds),
    )


class GeoLifeWindowFeatureTests(unittest.TestCase):
    def test_stationary_window_has_expected_summary(self) -> None:
        result = compute_window_features([make_point(0), make_point(5), make_point(10)])
        self.assertEqual(result["point_count"], 3)
        self.assertEqual(result["valid_step_count"], 2)
        self.assertEqual(result["distance_m"], 0.0)
        self.assertEqual(result["stop_ratio"], 1.0)
        self.assertEqual(result["gap_step_count"], 0)

    def test_long_gap_is_counted_and_excluded(self) -> None:
        result = compute_window_features([make_point(0), make_point(5, 39.001), make_point(200, 39.002)])
        self.assertEqual(result["gap_step_count"], 1)
        self.assertEqual(result["valid_step_count"], 1)

    def test_requires_two_points(self) -> None:
        with self.assertRaises(ValueError):
            compute_window_features([make_point(0)])


if __name__ == "__main__":
    unittest.main()
