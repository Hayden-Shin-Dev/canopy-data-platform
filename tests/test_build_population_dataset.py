from __future__ import annotations

import unittest

import pandas as pd

from src.build_population_dataset import OUTPUT_COLUMNS, _prepare_output


class BuildPopulationDatasetTests(unittest.TestCase):
    def test_prepare_output_adds_optional_distance_columns(self) -> None:
        source = pd.DataFrame(
            {
                "person_group_id": ["group-1"],
                "actual_mode": ["rail"],
                "actual_mode_sequence": ["walk|rail|walk"],
                "trip_id": ["trip-1"],
            }
        )

        result = _prepare_output(source)

        self.assertEqual(list(result.columns), list(OUTPUT_COLUMNS))
        self.assertTrue(pd.isna(result.loc[0, "od_straight_distance_km"]))
        self.assertTrue(pd.isna(result.loc[0, "distance_band"]))
        self.assertIn(result.loc[0, "split"], {"train", "validation", "test"})


if __name__ == "__main__":
    unittest.main()

