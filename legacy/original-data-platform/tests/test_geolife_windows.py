from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.geolife.raw import TrajectoryPoint
from src.geolife.windows import iter_time_windows


def make_point(seconds: int, trajectory_id: str = "sample") -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id="000",
        trajectory_id=trajectory_id,
        latitude=39.0,
        longitude=116.0,
        altitude_ft=0.0,
        timestamp=datetime(2020, 1, 1) + timedelta(seconds=seconds),
    )


class GeoLifeWindowTests(unittest.TestCase):
    def test_groups_points_by_trajectory_time_bucket(self) -> None:
        windows = list(
            iter_time_windows(
                [make_point(0), make_point(5), make_point(61), make_point(65)],
                window_seconds=60,
            )
        )
        self.assertEqual(len(windows), 2)
        self.assertEqual([len(window.points) for window in windows], [2, 2])
        self.assertEqual(windows[1].window_start, datetime(2020, 1, 1, 0, 1))

    def test_does_not_mix_trajectories(self) -> None:
        windows = list(
            iter_time_windows(
                [make_point(0, "a"), make_point(1, "a"), make_point(0, "b"), make_point(1, "b")],
                window_seconds=60,
            )
        )
        self.assertEqual([(item.trajectory_id, len(item.points)) for item in windows], [("a", 2), ("b", 2)])

    def test_rejects_backwards_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            list(iter_time_windows([make_point(0), make_point(61), make_point(30)], window_seconds=60))

    def test_validates_arguments(self) -> None:
        with self.assertRaises(ValueError):
            list(iter_time_windows([make_point(0), make_point(1)], window_seconds=0))


if __name__ == "__main__":
    unittest.main()
