from __future__ import annotations

import unittest

import pandas as pd

from src.ktdb.locations import derive_location_features


class LocationFeatureTests(unittest.TestCase):
    def test_od_scope_uses_the_most_specific_matching_area(self) -> None:
        source = pd.DataFrame(
            {
                "sTP1_1_5": ["A", "A", "A", "A", ""],
                "sTP1_1_6": ["서울", "서울", "서울", "서울", "서울"],
                "sTP1_1_7": ["강남", "강남", "강남", "강남", "강남"],
                "TP1_1_5": ["A", "B", "C", "D", "E"],
                "TP1_1_6": ["서울", "서울", "서울", "부산", "서울"],
                "TP1_1_7": ["강남", "강남", "종로", "해운대", "강남"],
            }
        )

        result = derive_location_features(source)

        self.assertEqual(
            result["od_scope"].iloc[:4].tolist(),
            ["same_dong", "same_sigungu", "same_sido", "inter_sido"],
        )
        self.assertTrue(pd.isna(result.loc[4, "od_scope"]))


if __name__ == "__main__":
    unittest.main()
