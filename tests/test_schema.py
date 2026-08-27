from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.schema import MODEL_FEATURES, TRIP_BASE_COLUMNS, trip_columns


class SchemaTests(unittest.TestCase):
    def test_trip_columns_match_the_raw_header(self) -> None:
        header = pd.read_csv(
            "data/raw/ktdb/②이동특성.csv",
            encoding="cp949",
            nrows=0,
        ).columns

        self.assertTrue(set(trip_columns()).issubset(set(header)))
        self.assertEqual(len(TRIP_BASE_COLUMNS), 21)

    def test_model_features_do_not_include_identifiers_or_targets(self) -> None:
        forbidden = {"idx", "fid", "person_group_id", "actual_mode", "split"}

        self.assertTrue(set(MODEL_FEATURES).isdisjoint(forbidden))
        self.assertEqual(len(MODEL_FEATURES), 15)


if __name__ == "__main__":
    unittest.main()
