from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.time_features import derive_time_features, parse_survey_date


class TimeFeatureTests(unittest.TestCase):
    def test_parse_survey_date_uses_yyyymmdd(self) -> None:
        dates = parse_survey_date(pd.Series(["1021", "1201", ""]))

        self.assertEqual(str(dates.iloc[0].date()), "2021-10-21")
        self.assertEqual(str(dates.iloc[1].date()), "2021-12-01")
        self.assertTrue(pd.isna(dates.iloc[2]))

    def test_departure_boundaries_and_rollover(self) -> None:
        source = pd.DataFrame(
            {
                "DATE": ["1021", "1021", "1021", "1021"],
                "TP3_1": [7, 17, 24, ""],
                "TP3_2": [14, 45, 5, 33],
            }
        )

        result = derive_time_features(source)

        self.assertEqual(result.loc[0, "departure_minute_bin"], 0)
        self.assertEqual(result.loc[0, "time_band"], "morning_peak")
        self.assertEqual(result.loc[1, "departure_minute_bin"], 45)
        self.assertEqual(result.loc[1, "time_band"], "evening_peak")
        self.assertEqual(result.loc[2, "departure_hour"], 0)
        self.assertEqual(result.loc[2, "time_band"], "late_night")
        self.assertTrue(pd.isna(result.loc[3, "departure_hour"]))


if __name__ == "__main__":
    unittest.main()

