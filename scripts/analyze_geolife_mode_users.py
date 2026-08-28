"""GeoLife split별 mode 사용자 수와 Window 수를 집계한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SPLITS = ("train", "validation", "test")


def analyze_mode_users(dataset_csv: str | Path) -> dict[str, object]:
    frame = pd.read_csv(
        dataset_csv,
        encoding="utf-8-sig",
        dtype={"user_id": "string", "canonical_mode": "string", "split": "string"},
    )
    required = {"user_id", "canonical_mode", "split"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"분석에 필요한 column이 없습니다: {missing}")
    result: dict[str, object] = {"dataset_csv": str(dataset_csv), "splits": {}}
    for split in SPLITS:
        subset = frame[frame["split"] == split]
        modes: dict[str, object] = {}
        for mode in sorted(subset["canonical_mode"].dropna().unique()):
            mode_subset = subset[subset["canonical_mode"] == mode]
            modes[str(mode)] = {
                "user_count": int(mode_subset["user_id"].nunique()),
                "window_count": int(len(mode_subset)),
                "users": sorted(mode_subset["user_id"].astype(str).unique().tolist()),
            }
        result["splits"][split] = {"user_count": int(subset["user_id"].nunique()), "modes": modes}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    args = parser.parse_args()
    print(json.dumps(analyze_mode_users(args.dataset_csv), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
