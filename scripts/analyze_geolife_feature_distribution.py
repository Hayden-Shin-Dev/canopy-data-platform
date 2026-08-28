"""GeoLife mode별 Window Feature 분포를 비교한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


FEATURES = (
    "mean_speed_mps",
    "max_speed_mps",
    "speed_std_mps",
    "mean_abs_acceleration_mps2",
    "stop_ratio",
    "distance_m",
    "displacement_m",
    "straightness_ratio",
    "mean_heading_change_deg",
)


def analyze_feature_distribution(dataset_csv: str | Path) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"canonical_mode": "string"})
    required = set(FEATURES) | {"canonical_mode"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"분석에 필요한 column이 없습니다: {missing}")
    rows: dict[str, object] = {}
    for mode, subset in frame.groupby("canonical_mode", sort=True):
        feature_summary: dict[str, object] = {}
        for feature in FEATURES:
            values = pd.to_numeric(subset[feature], errors="coerce").dropna()
            quantiles = values.quantile([0.25, 0.50, 0.75])
            feature_summary[feature] = {
                "count": int(values.size),
                "p25": float(quantiles.loc[0.25]),
                "median": float(quantiles.loc[0.50]),
                "p75": float(quantiles.loc[0.75]),
            }
        rows[str(mode)] = feature_summary
    return {"dataset_csv": str(dataset_csv), "features": list(FEATURES), "modes": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    args = parser.parse_args()
    print(json.dumps(analyze_feature_distribution(args.dataset_csv), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
