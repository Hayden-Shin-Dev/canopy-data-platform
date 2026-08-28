from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.geolife.label_match import LabeledPoint
from src.geolife.labeled_windows import iter_labeled_time_windows
from src.geolife.raw import TrajectoryPoint


def labeled(seconds: int, trajectory_id: str = "sample") -> LabeledPoint:
    point = TrajectoryPoint(
        "000",
        trajectory_id,
        39.0,
        116.0,
        0.0,
        datetime(2020, 1, 1) + timedelta(seconds=seconds),
    )
    return LabeledPoint(point, "walk", "matched")


class GeoLifeLabeledWindowTests(unittest.TestCase):
    def test_keeps_labels_inside_each_window(self) -> None:
        windows = list(
            iter_labeled_time_windows(
                [labeled(0), labeled(5), labeled(61), labeled(65)],
                window_seconds=60,
            )
        )
        self.assertEqual(len(windows), 2)
        self.assertEqual([len(window.points) for window in windows], [2, 2])
        self.assertEqual(windows[1].points[0].mode_raw, "walk")

    def test_rejects_backwards_window_bucket(self) -> None:
        with self.assertRaises(ValueError):
            list(iter_labeled_time_windows([labeled(0), labeled(61), labeled(30)], window_seconds=60))

    def test_validates_arguments(self) -> None:
        with self.assertRaises(ValueError):
            list(iter_labeled_time_windows([labeled(0), labeled(1)], window_seconds=0))


if __name__ == "__main__":
    unittest.main()
