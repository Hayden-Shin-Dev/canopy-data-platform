from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.codebook import Codebook
from src.ktdb.schema import trip_columns
from src.ktdb.transform import build_feature_frame


class TransformTests(unittest.TestCase):
    def test_builder_joins_date_and_keeps_only_five_classes(self) -> None:
        codebook = Codebook(
            variable_labels={},
            values={
                "TP2": {"3": "출근"},
                "TP5_1": {"1": "걸어서/도보", "13": "오토바이"},
            },
            sheets=(),
        )
        row = {column: "" for column in trip_columns()}
        row.update(
            {
                "idx": "person-1",
                "fid": "trip-1",
                "sTP1": "1",
                "TP1": "2",
                "sTP1_1_5": "A",
                "sTP1_1_6": "서울",
                "sTP1_1_7": "강남",
                "TP1_1_5": "B",
                "TP1_1_6": "서울",
                "TP1_1_7": "강남",
                "TP2": "3",
                "TP3_1": "8",
                "TP3_2": "10",
                "TP5_1": "1",
                "TP5_1_t1": "7",
            }
        )
        excluded = row.copy()
        excluded.update({"fid": "trip-2", "TP5_1": "13"})
        trips = pd.DataFrame([row, excluded])
        persons = pd.DataFrame({"idx": ["person-1"], "DATE": ["1021"]})

        result = build_feature_frame(trips, persons, codebook)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "actual_mode"], "walk")
        self.assertEqual(result.loc[0, "survey_date"], "2021-10-21")
        self.assertEqual(result.loc[0, "commute_direction"], "to_work")
        self.assertEqual(len(result.loc[0, "person_group_id"]), 16)


if __name__ == "__main__":
    unittest.main()
