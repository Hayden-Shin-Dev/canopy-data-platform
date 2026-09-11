"""KTDB 행정동 매칭과 직선거리 생성 결과 요약."""

from __future__ import annotations

import pandas as pd

from src.config import DISTANCE_BANDS


def _rate(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else 0.0


def summarize_distance_coverage(
    frame: pd.DataFrame,
    *,
    sgis_admin_dong_count: int,
    unmatched: pd.DataFrame,
) -> dict[str, object]:
    required = {
        "origin_x",
        "origin_y",
        "destination_x",
        "destination_y",
        "od_straight_distance_km",
        "distance_band",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"거리 validation에 필요한 컬럼이 없습니다: {missing}")

    origin_matched = frame[["origin_x", "origin_y"]].notna().all(axis=1)
    destination_matched = frame[["destination_x", "destination_y"]].notna().all(axis=1)
    distance = pd.to_numeric(frame["od_straight_distance_km"], errors="coerce")
    successful = distance.notna()
    valid_distance = distance[successful]
    band_counts = frame["distance_band"].value_counts(dropna=True)

    statistics = {
        "minimum_km": float(valid_distance.min()) if len(valid_distance) else None,
        "median_km": float(valid_distance.median()) if len(valid_distance) else None,
        "mean_km": float(valid_distance.mean()) if len(valid_distance) else None,
        "maximum_km": float(valid_distance.max()) if len(valid_distance) else None,
    }
    return {
        "sgis_admin_dong_count": int(sgis_admin_dong_count),
        "origin_match_rate": _rate(origin_matched),
        "destination_match_rate": _rate(destination_matched),
        "distance_success_rows": int(successful.sum()),
        "distance_failure_rows": int((~successful).sum()),
        "unmatched_admin_dong_count": int(unmatched["ktdb_admin_code"].nunique()) if len(unmatched) else 0,
        "distance_statistics": statistics,
        "distance_band_counts": {
            label: int(band_counts.get(label, 0)) for label, _, _ in DISTANCE_BANDS
        },
    }
