"""GeoLife Raw label/trajectory와 processed Window 사이의 lineage를 확인한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from src.geolife.mode_mapping import CANOPY_MODES, canonicalize_mode
from src.geolife.raw import iter_label_intervals, iter_trajectory_points


def validate_lineage(raw_source: str | Path, processed_csv: str | Path) -> dict[str, object]:
    labels = list(iter_label_intervals(raw_source))
    raw_mode_counts = Counter()
    for label in labels:
        mode = canonicalize_mode(label.mode_raw)
        if mode is not None:
            raw_mode_counts[mode] += 1

    raw_users: set[str] = set()
    raw_trajectories: set[tuple[str, str]] = set()
    raw_point_count = 0
    for point in iter_trajectory_points(raw_source, strict=False):
        raw_point_count += 1
        raw_users.add(point.user_id)
        raw_trajectories.add((point.user_id, point.trajectory_id))

    frame = pd.read_csv(processed_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"user_id", "trajectory_id", "canonical_mode", "window_start", "window_end", "split"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"processed CSV required columns missing: {missing}")
    processed_mode_counts = frame["canonical_mode"].value_counts().to_dict()
    processed_users = set(frame["user_id"].dropna().astype(str))
    processed_trajectories = set(zip(frame["user_id"].astype(str), frame["trajectory_id"].astype(str)))
    invalid_modes = sorted(set(processed_mode_counts) - set(CANOPY_MODES))
    empty_modes = sorted(mode for mode in CANOPY_MODES if processed_mode_counts.get(mode, 0) == 0)
    trajectory_overlap = len(processed_trajectories & raw_trajectories)
    result = {
        "raw_source": str(raw_source),
        "processed_csv": str(processed_csv),
        "raw": {
            "point_count": raw_point_count,
            "user_count": len(raw_users),
            "trajectory_count": len(raw_trajectories),
            "canonical_label_interval_counts": dict(sorted(raw_mode_counts.items())),
        },
        "processed": {
            "window_count": len(frame),
            "user_count": len(processed_users),
            "trajectory_count": len(processed_trajectories),
            "mode_counts": {str(k): int(v) for k, v in sorted(processed_mode_counts.items())},
            "split_counts": {str(k): int(v) for k, v in frame["split"].value_counts().items()},
        },
        "lineage": {
            "processed_users_subset_of_raw": processed_users.issubset(raw_users),
            "processed_trajectories_matching_raw": trajectory_overlap,
            "processed_trajectories_missing_from_raw": len(processed_trajectories - raw_trajectories),
            "invalid_processed_modes": invalid_modes,
            "empty_canonical_modes": empty_modes,
            "all_canonical_modes_have_raw_labels": all(raw_mode_counts.get(mode, 0) > 0 for mode in CANOPY_MODES),
        },
    }
    result["passed"] = not invalid_modes and result["lineage"]["processed_users_subset_of_raw"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_source")
    parser.add_argument("processed_csv")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_lineage(args.raw_source, args.processed_csv)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
