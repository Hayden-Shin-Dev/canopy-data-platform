from __future__ import annotations

import unittest
from datetime import datetime

from src.geolife.label_match import LabeledPoint
from src.geolife.raw import TrajectoryPoint
from src.geolife.window_labels import summarize_window_labels


def labeled(mode: str | None, status: str = "matched") -> LabeledPoint:
    point = TrajectoryPoint("000", "sample", 39.0, 116.0, 0.0, datetime(2020, 1, 1))
    return LabeledPoint(point, mode, status)  # type: ignore[arg-type]


class GeoLifeWindowLabelTests(unittest.TestCase):
    def test_unique_majority_is_candidate(self) -> None:
        result = summarize_window_labels([labeled("bus"), labeled("bus"), labeled("walk")])
        self.assertEqual(result.status, "labeled")
        self.assertEqual(result.canonical_mode, "bus")
        self.assertEqual(result.mode_counts, {"bus": 2, "walk": 1})
        self.assertAlmostEqual(result.coverage, 1.0)

    def test_tie_is_ambiguous(self) -> None:
        result = summarize_window_labels([labeled("bus"), labeled("walk")])
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.canonical_mode)

    def test_unmatched_and_excluded_points_are_preserved(self) -> None:
        result = summarize_window_labels(
            [labeled("bus"), labeled(None, status="unmatched"), labeled("airplane")]
        )
        self.assertEqual(result.canonical_mode, "bus")
        self.assertEqual(result.matched_point_count, 2)
        self.assertEqual(result.excluded_point_count, 1)
        self.assertEqual(result.ambiguous_point_count, 0)

    def test_empty_window_is_unlabeled(self) -> None:
        result = summarize_window_labels([])
        self.assertEqual(result.status, "unlabeled")
        self.assertEqual(result.coverage, 0.0)


if __name__ == "__main__":
    unittest.main()
