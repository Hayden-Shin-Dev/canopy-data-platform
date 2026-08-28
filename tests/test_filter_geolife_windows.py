import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.filter_geolife_windows import filter_by_mode_purity


class FilterGeoLifeWindowsTests(unittest.TestCase):
    def test_filters_below_configured_purity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.csv"
            output = root / "output.csv"
            pd.DataFrame(
                {
                    "user_id": ["001", "002"],
                    "canonical_mode": ["walk", "bus"],
                    "canonical_mode_purity": [1.0, 0.75],
                    "split": ["train", "validation"],
                }
            ).to_csv(source, index=False, encoding="utf-8-sig")

            result = filter_by_mode_purity(source, output, min_mode_purity=0.8)

        self.assertEqual(result["selected_window_count"], 1)
        self.assertEqual(result["purity_rejected_count"], 1)
        self.assertEqual(result["mode_counts"], {"walk": 1})


if __name__ == "__main__":
    unittest.main()
