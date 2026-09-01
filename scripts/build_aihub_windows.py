"""Create a reproducible, streaming AI-Hub trajectory feature table."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.aihub.features import AIHUB_FEATURE_COLUMNS, feature_row
from src.aihub.ingest import iter_gps_files, read_trajectory


METADATA_COLUMNS = (
    "user_id",
    "trajectory_id",
    "source_class",
    "canonical_mode",
    "window_start",
    "window_end",
    "raw_point_count",
    "missing_coordinate_count",
    "invalid_coordinate_count",
    "duplicate_timestamp_count",
    "backwards_timestamp_count",
    "gap_count",
    "raw_label_values",
    "split",
)


def build_dataset(
    source_root: str | Path,
    output_csv: str | Path,
    *,
    split: str = "Training",
    workers: int = 1,
) -> dict[str, object]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [*METADATA_COLUMNS, *AIHUB_FEATURE_COLUMNS]
    counts: Counter[str] = Counter()
    selected = Counter()
    excluded = Counter()
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        files = iter_gps_files(source_root, split)
        if workers == 1:
            trajectories = (
                read_trajectory(source_class, gps_path, label_path)
                for source_class, gps_path, label_path in files
            )
        else:
            executor = ThreadPoolExecutor(max_workers=workers)
            trajectories = executor.map(
                lambda item: read_trajectory(*item),
                files,
                buffersize=max(2, workers * 2),
            )
        try:
            for trajectory in trajectories:
                counts[trajectory.canonical_mode] += 1
                try:
                    row = feature_row(trajectory)
                except ValueError:
                    excluded[trajectory.canonical_mode] += 1
                    continue
                row["split"] = split.lower()
                writer.writerow(row)
                selected[trajectory.canonical_mode] += 1
        finally:
            if workers > 1:
                executor.shutdown(wait=True)
    summary = {
        "source_root": str(source_root),
        "source_split": split,
        "output_csv": str(output_path),
        "feature_version": "aihub-window-v1",
        "workers": workers,
        "trajectory_count": sum(counts.values()),
        "selected_count": sum(selected.values()),
        "excluded_count": sum(excluded.values()),
        "source_class_counts": dict(sorted(counts.items())),
        "selected_class_counts": dict(sorted(selected.items())),
        "excluded_class_counts": dict(sorted(excluded.items())),
        "feature_columns": list(AIHUB_FEATURE_COLUMNS),
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root")
    parser.add_argument("output_csv")
    parser.add_argument("--split", choices=("Training", "Validation"), default="Training")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(build_dataset(args.source_root, args.output_csv, split=args.split, workers=args.workers), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
