from __future__ import annotations

import pandas as pd

from src.ktdb.distance_report import summarize_distance_coverage


def test_summarize_distance_coverage_reports_rates_statistics_and_bands() -> None:
    frame = pd.DataFrame(
        {
            "origin_x": [1.0, 1.0, pd.NA],
            "origin_y": [2.0, 2.0, pd.NA],
            "destination_x": [3.0, pd.NA, 3.0],
            "destination_y": [4.0, pd.NA, 4.0],
            "od_straight_distance_km": [1.0, pd.NA, pd.NA],
            "distance_band": ["0-2km", pd.NA, pd.NA],
        }
    )
    unmatched = pd.DataFrame(
        {
            "ktdb_admin_code": ["missing", "missing"],
            "side": ["origin", "destination"],
        }
    )

    result = summarize_distance_coverage(frame, sgis_admin_dong_count=3500, unmatched=unmatched)

    assert result["sgis_admin_dong_count"] == 3500
    assert result["origin_match_rate"] == 2 / 3
    assert result["destination_match_rate"] == 2 / 3
    assert result["distance_success_rows"] == 1
    assert result["distance_failure_rows"] == 2
    assert result["unmatched_admin_dong_count"] == 1
    assert result["distance_statistics"] == {
        "minimum_km": 1.0,
        "median_km": 1.0,
        "mean_km": 1.0,
        "maximum_km": 1.0,
    }
    assert result["distance_band_counts"]["0-2km"] == 1
    assert result["distance_band_counts"]["20km+"] == 0
