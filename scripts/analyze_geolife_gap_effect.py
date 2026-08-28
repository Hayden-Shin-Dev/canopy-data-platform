"""GeoLife Window의 sampling gap 분포를 mode별로 집계한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_gap_effect(dataset_csv: str | Path) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"canonical_mode": "string"})
    required = {"canonical_mode", "gap_step_count", "avg_sampling_interval_sec", "valid_step_count"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"분석에 필요한 column이 없습니다: {missing}")
    rows: dict[str, object] = {}
    for mode, subset in frame.groupby("canonical_mode", sort=True):
        gaps = pd.to_numeric(subset["gap_step_count"], errors="coerce").fillna(0)
        intervals = pd.to_numeric(subset["avg_sampling_interval_sec"], errors="coerce").dropna()
        valid_steps = pd.to_numeric(subset["valid_step_count"], errors="coerce").fillna(0)
        rows[str(mode)] = {
            "window_count": int(len(subset)),
            "windows_with_gap": int((gaps > 0).sum()),
            "gap_window_ratio": float((gaps > 0).mean()),
            "gap_step_total": int(gaps.sum()),
            "gap_step_median": float(gaps.median()),
            "valid_step_median": float(valid_steps.median()),
            "avg_sampling_interval_median_sec": float(intervals.median()),
        }
    return {"dataset_csv": str(dataset_csv), "modes": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    args = parser.parse_args()
    print(json.dumps(analyze_gap_effect(args.dataset_csv), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
