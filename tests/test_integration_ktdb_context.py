from datetime import datetime, timezone

import pandas as pd

from src.integration.gps_contract import GpsEvent
from src.integration.ktdb_context import build_expected_features


def _events() -> list[GpsEvent]:
    return [
        GpsEvent("1.0", "trip", "device", 0, datetime(2026, 8, 28, 23, 0, tzinfo=timezone.utc), 37.52, 126.91, 5, 10, 5, 1, 90),
        GpsEvent("1.0", "trip", "device", 1, datetime(2026, 8, 28, 23, 5, tzinfo=timezone.utc), 37.57, 126.98, 5, 10, 5, 1, 90),
    ]


def test_build_expected_features_uses_centroid_mapping_and_real_time(tmp_path):
    centroids = tmp_path / "centroids.csv"
    pd.DataFrame(
        [
            {"adm_cd": "sgis-origin", "adm_nm": "서울특별시 영등포구 영등포동", "x": 947659, "y": 1947092, "source_crs": "EPSG:5179", "reference_year": 2021},
            {"adm_cd": "sgis-destination", "adm_nm": "서울특별시 종로구 사직동", "x": 953230, "y": 1952854, "source_crs": "EPSG:5179", "reference_year": 2021},
        ]
    ).to_csv(centroids, index=False)
    mapping = tmp_path / "mapping.csv"
    pd.DataFrame(
        [
            {"ktdb_admin_code": "1156053500", "ktdb_full_name": "서울특별시 영등포구 영등포동", "sgis_adm_cd": "sgis-origin"},
            {"ktdb_admin_code": "1111053000", "ktdb_full_name": "서울특별시 종로구 사직동", "sgis_adm_cd": "sgis-destination"},
        ]
    ).to_csv(mapping, index=False)
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame([{"purpose": "출근", "commute_direction": "to_work"}]).to_csv(dataset, index=False, encoding="utf-8-sig")

    scenario = build_expected_features(_events(), dataset_path=dataset, centroids_path=centroids, mapping_path=mapping)

    assert scenario.features["weekday"] == "Sat"
    assert scenario.features["departure_hour"] == 8
    assert scenario.features["origin_admin_dong"] == "1156053500"
    assert scenario.features["destination_admin_dong"] == "1111053000"
    assert scenario.features["commute_direction"] == "to_work"
    assert scenario.features["od_straight_distance_km"] > 0
    assert scenario.provenance["purpose_source"].startswith("KTDB")
