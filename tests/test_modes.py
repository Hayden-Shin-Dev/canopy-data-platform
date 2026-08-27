from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.codebook import Codebook
from src.ktdb.modes import derive_mode_features


class ModeFeatureTests(unittest.TestCase):
    def test_longest_duration_wins_over_access_walk(self) -> None:
        codebook = Codebook(
            variable_labels={},
            values={
                "TP5_1": {
                    "1": "걸어서/도보",
                    "2": "승용차/승합차",
                    "7": "지하철/전철/경전철",
                }
            },
            sheets=(),
        )
        source = pd.DataFrame(
            {
                "TP5_1": ["1", "1", "13"],
                "TP5_1_t1": ["2", "7", "1"],
                "TP5_2": ["7", "", ""],
                "TP5_2_t1": ["10", "", ""],
            }
        )

        result = derive_mode_features(source, codebook)

        self.assertEqual(result.loc[0, "actual_mode_sequence"], "walk|rail")
        self.assertEqual(result.loc[0, "actual_mode"], "rail")
        self.assertEqual(result.loc[1, "actual_mode"], "walk")
        self.assertEqual(result.loc[2, "actual_mode"], "")


if __name__ == "__main__":
    unittest.main()

