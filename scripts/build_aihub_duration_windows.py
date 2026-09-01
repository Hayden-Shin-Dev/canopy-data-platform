"""Build longer AI-Hub windows without changing the source files.

AI-Hub TMC files are usually one minute long.  This builder joins only
chronologically adjacent files from the same user and class, so the model
can be trained on the duration used by the production replay evaluator.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from src.aihub.features import AIHUB_FEATURE_COLUMNS, compute_aihub_features
from src.aihub.ingest import AiHubTrajectory, iter_trajectories


METADATA_COLUMNS = (
    "user_id", "trajectory_id", "source_class", "canonical_mode",
    "window_start", "window_end", "split", "raw_point_count",
    "missing_coordinate_count", "invalid_coordinate_count",
    "duplicate_timestamp_count", "backwards_timestamp_count", "gap_count",
    "raw_label_values",
)


def _split_map(path: str | Path) -> dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(item["user_id"]): str(item["split"]) for item in payload["groups"]}


def _join(left: AiHubTrajectory, right: AiHubTrajectory) -> dict[str, object] | None:
    if left.user_id != right.user_id or left.canonical_mode != right.canonical_mode:
        return None
    if right.points[0].timestamp < left.points[-1].timestamp:
        return None
    gap = right.points[0].timestamp - left.points[-1].timestamp
    if gap > timedelta(seconds=30):
        return None
    points = tuple([*left.points, *right.points])
    if len(points) < 2:
        return None
    class _Combined:
        pass
    combined = _Combined()
    combined.user_id = left.user_id
    combined.trajectory_id = f"{left.trajectory_id}__{right.trajectory_id}"
    combined.canonical_mode = left.canonical_mode
    combined.points = points
    combined.raw_point_count = left.raw_point_count + right.raw_point_count
    combined.missing_coordinate_count = left.missing_coordinate_count + right.missing_coordinate_count
    combined.invalid_coordinate_count = left.invalid_coordinate_count + right.invalid_coordinate_count
    combined.duplicate_timestamp_count = left.duplicate_timestamp_count + right.duplicate_timestamp_count
    combined.backwards_timestamp_count = left.backwards_timestamp_count + right.backwards_timestamp_count
    combined.gap_count = left.gap_count + right.gap_count
    combined.raw_label_values = tuple(sorted(set(left.raw_label_values) | set(right.raw_label_values)))
    return {
        "user_id": combined.user_id,
        "trajectory_id": combined.trajectory_id,
        "source_class": left.source_class,
        "canonical_mode": combined.canonical_mode,
        "window_start": points[0].timestamp.isoformat(sep=" "),
        "window_end": points[-1].timestamp.isoformat(sep=" "),
        "raw_point_count": combined.raw_point_count,
        "missing_coordinate_count": combined.missing_coordinate_count,
        "invalid_coordinate_count": combined.invalid_coordinate_count,
        "duplicate_timestamp_count": combined.duplicate_timestamp_count,
        "backwards_timestamp_count": combined.backwards_timestamp_count,
        "gap_count": combined.gap_count,
        "raw_label_values": "|".join(combined.raw_label_values),
        **compute_aihub_features(combined),
    }


def build_dataset(source_root: str | Path, split_manifest: str | Path, output_csv: str | Path) -> dict[str, object]:
    split_by_user = _split_map(split_manifest)
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = [*METADATA_COLUMNS, *AIHUB_FEATURE_COLUMNS]
    previous: dict[str, AiHubTrajectory] = {}
    counts: Counter[str] = Counter()
    selected: Counter[str] = Counter()
    seen = set()
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for source_split in ("Training", "Validation"):
            # Label files were paired and timestamp-validated during the input
            # audit.  Re-read only GPS here; this keeps the duration experiment
            # focused on geometry and avoids duplicating that I/O.
            for trajectory in iter_trajectories(
                source_root,
                source_split,
                strict_label_timestamps=False,
                read_label_content=False,
            ):
                user_split = split_by_user.get(str(int(trajectory.user_id)))
                if user_split is None:
                    continue
                counts[trajectory.canonical_mode] += 1
                prior = previous.get(trajectory.user_id)
                if prior is not None:
                    row = _join(prior, trajectory)
                    if row is not None:
                        key = row["trajectory_id"]
                        if key not in seen:
                            row["split"] = user_split
                            writer.writerow(row)
                            seen.add(key)
                            selected[trajectory.canonical_mode] += 1
                previous[trajectory.user_id] = trajectory
    summary = {"source_root": str(source_root), "output_csv": str(output), "window_seconds": 120,
               "group_column": "user_id", "source_trajectory_count": sum(counts.values()),
               "selected_window_count": sum(selected.values()),
               "source_class_counts": dict(sorted(counts.items())),
               "selected_class_counts": dict(sorted(selected.items())),
               "feature_columns": list(AIHUB_FEATURE_COLUMNS)}
    output.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root")
    parser.add_argument("split_manifest")
    parser.add_argument("output_csv")
    args = parser.parse_args()
    print(json.dumps(build_dataset(args.source_root, args.split_manifest, args.output_csv), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
