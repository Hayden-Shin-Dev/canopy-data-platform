from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.purpose import derive_commute_direction, filter_commute


class PurposeFeatureTests(unittest.TestCase):
    def test_commute_direction_requires_purpose_and_place_codes(self) -> None:
        source = pd.DataFrame(
            {
                "TP2": ["3", "1", "3", "1", "7"],
                "sTP1": ["1", "2", "2", "1", "1"],
                "TP1": ["2", "1", "1", "2", "2"],
            }
        )

        result = derive_commute_direction(source)

        self.assertEqual(
            result["commute_direction"].tolist(),
            ["to_work", "work_to_home", "non_commute", "non_commute", "non_commute"],
        )
        self.assertEqual(len(filter_commute(result)), 2)


if __name__ == "__main__":
    unittest.main()

