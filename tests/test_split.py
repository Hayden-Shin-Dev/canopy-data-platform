from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.split import assign_group_split, split_for_group


class SplitTests(unittest.TestCase):
    def test_same_group_always_gets_one_split(self) -> None:
        frame = pd.DataFrame(
            {
                "person_group_id": ["p1", "p1", "p2", "p3", "p4"],
            }
        )

        first = assign_group_split(frame)
        second = assign_group_split(frame.sample(frac=1, random_state=3))

        self.assertEqual(first.iloc[0], first.iloc[1])
        self.assertEqual(split_for_group("p1"), first.iloc[0])
        self.assertEqual(
            set(zip(frame["person_group_id"], first)),
            set(zip(frame.sample(frac=1, random_state=3)["person_group_id"], second)),
        )

    def test_missing_group_column_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assign_group_split(pd.DataFrame({"idx": [1]}))


if __name__ == "__main__":
    unittest.main()

