from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from src.geolife.label_match import iter_labeled_points, match_point
from src.geolife.raw import LabelInterval, TrajectoryPoint


BASE_TIME = datetime(2020, 1, 1, 8, 0, 0)


def point(offset_seconds: int, user_id: str = "000") -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id=user_id,
        trajectory_id="sample",
        latitude=39.0,
        longitude=116.0,
        altitude_ft=100.0,
        timestamp=BASE_TIME + timedelta(seconds=offset_seconds),
    )


def label(start: int, end: int, mode: str = "bus", user_id: str = "000") -> LabelInterval:
    return LabelInterval(
        user_id=user_id,
        start_time=BASE_TIME + timedelta(seconds=start),
        end_time=BASE_TIME + timedelta(seconds=end),
        mode_raw=mode,
    )


class GeoLifeLabelMatchTests(unittest.TestCase):
    def test_matches_inclusive_interval(self) -> None:
        result = match_point(point(10), [label(10, 20)])
        self.assertEqual(result.match_status, "matched")
        self.assertEqual(result.mode_raw, "bus")

    def test_unmatched_point_has_no_mode(self) -> None:
        result = match_point(point(30), [label(10, 20)])
        self.assertEqual(result.match_status, "unmatched")
        self.assertIsNone(result.mode_raw)

    def test_overlapping_intervals_are_ambiguous(self) -> None:
        result = match_point(point(15), [label(10, 20), label(15, 25, mode="train")])
        self.assertEqual(result.match_status, "ambiguous")
        self.assertIsNone(result.mode_raw)

    def test_stream_matching_keeps_user_boundaries(self) -> None:
        results = list(
            iter_labeled_points(
                [point(10), point(30), point(10, user_id="001")],
                [label(0, 20), label(0, 20, user_id="001", mode="walk")],
            )
        )
        self.assertEqual([item.match_status for item in results], ["matched", "unmatched", "matched"])
        self.assertEqual(results[2].mode_raw, "walk")


if __name__ == "__main__":
    unittest.main()
