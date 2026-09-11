from __future__ import annotations

import pandas as pd

from src.ktdb.admin_centroids import SGIS_SOURCE_CRS
from src.ktdb.admin_matching import (
    attach_admin_centroids,
    build_admin_centroid_mapping,
    build_unmatched_report,
    inspect_code_systems,
)


def _admin_lookup() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "admin_code": ["1111053000", "1111054000", "9999999999"],
            "sido": ["서울특별시", "서울특별시", "없는시"],
            "sigungu": ["종로구", "종로구", "없는구"],
            "admin_name": ["사직동", "삼청동", "없는동"],
        }
    )


def _centroids() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "adm_cd": ["1101053", "1101054"],
            "adm_nm": ["서울특별시 종로구 사직동", "서울특별시 종로구 삼청동"],
            "x": [953808.5, 954100.0],
            "y": [1952441.25, 1953000.0],
            "source_crs": [SGIS_SOURCE_CRS, SGIS_SOURCE_CRS],
            "reference_year": ["2021", "2021"],
        }
    )


def test_inspect_code_systems_records_10_to_7_digit_difference() -> None:
    result = inspect_code_systems(_admin_lookup(), _centroids())

    assert result["ktdb_code_lengths"] == {10: 3}
    assert result["sgis_code_lengths"] == {7: 2}
    assert result["direct_code_overlap"] == 0
    assert result["mapping_method"] == "exact_full_admin_name"


def test_build_admin_centroid_mapping_uses_exact_full_name() -> None:
    mapping = build_admin_centroid_mapping(_admin_lookup(), _centroids()).set_index("ktdb_admin_code")

    assert mapping.loc["1111053000", "sgis_adm_cd"] == "1101053"
    assert mapping.loc["1111054000", "match_status"] == "matched"
    assert mapping.loc["9999999999", "match_status"] == "name_not_found"


def test_attach_admin_centroids_keeps_unmatched_coordinates_missing() -> None:
    mapping = build_admin_centroid_mapping(_admin_lookup(), _centroids())
    trips = pd.DataFrame(
        {
            "origin_admin_dong": ["1111053000", "9999999999"],
            "destination_admin_dong": ["1111054000", "1111053000"],
        }
    )

    result = attach_admin_centroids(trips, mapping)

    assert result.loc[0, "origin_x"] == 953808.5
    assert result.loc[0, "destination_y"] == 1953000.0
    assert pd.isna(result.loc[1, "origin_x"])


def test_build_unmatched_report_counts_each_trip_side() -> None:
    mapping = build_admin_centroid_mapping(_admin_lookup(), _centroids())
    trips = attach_admin_centroids(
        pd.DataFrame(
            {
                "origin_admin_dong": ["9999999999", "9999999999"],
                "destination_admin_dong": ["1111053000", "8888888888"],
            }
        ),
        mapping,
    )

    report = build_unmatched_report(trips, mapping).set_index(["side", "ktdb_admin_code"])

    assert report.loc[("origin", "9999999999"), "row_count"] == 2
    assert report.loc[("origin", "9999999999"), "match_status"] == "name_not_found"
    assert report.loc[("destination", "8888888888"), "match_status"] == "code_not_in_lookup"
