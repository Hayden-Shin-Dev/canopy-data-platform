from __future__ import annotations

import unittest

import pandas as pd

from src.geolife.split import apply_group_split_map, assign_group_splits


class GeoLifeSplitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "user_id": [f"{index:03d}" for index in range(10) for _ in range(2)],
                "value": range(20),
            }
        )

    def test_groups_are_disjoint(self) -> None:
        result = assign_group_splits(self.frame)
        groups = {
            split: set(result.loc[result["split"] == split, "user_id"])
            for split in ("train", "validation", "test")
        }
        self.assertFalse(groups["train"] & groups["validation"])
        self.assertFalse(groups["train"] & groups["test"])
        self.assertFalse(groups["validation"] & groups["test"])

    def test_assignment_is_deterministic(self) -> None:
        first = assign_group_splits(self.frame)
        second = assign_group_splits(self.frame)
        self.assertEqual(first["split"].tolist(), second["split"].tolist())

    def test_requires_three_groups(self) -> None:
        with self.assertRaises(ValueError):
            assign_group_splits(self.frame[self.frame["user_id"] < "002"])

    def test_applies_reference_group_split_map(self) -> None:
        frame = pd.DataFrame({"user_id": ["010", "020", "010"]})
        result = apply_group_split_map(frame, {"010": "validation", "020": "test"})
        self.assertEqual(result["split"].tolist(), ["validation", "test", "validation"])

    def test_rejects_group_missing_from_reference_map(self) -> None:
        frame = pd.DataFrame({"user_id": ["010", "030"]})
        with self.assertRaises(ValueError):
            apply_group_split_map(frame, {"010": "train"})


if __name__ == "__main__":
    unittest.main()
