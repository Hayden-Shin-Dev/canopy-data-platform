from __future__ import annotations

import unittest

from src.geolife.segments import merge_consecutive_predictions


class GeoLifeSegmentTests(unittest.TestCase):
    def test_merges_consecutive_modes(self) -> None:
        segments = merge_consecutive_predictions(["walk", "walk", "bus", "bus", "walk"])
        self.assertEqual([(item.mode, item.start_index, item.end_index) for item in segments], [
            ("walk", 0, 1),
            ("bus", 2, 3),
            ("walk", 4, 4),
        ])
        self.assertEqual([item.window_count for item in segments], [2, 2, 1])

    def test_empty_sequence_returns_no_segments(self) -> None:
        self.assertEqual(merge_consecutive_predictions([]), [])


if __name__ == "__main__":
    unittest.main()
