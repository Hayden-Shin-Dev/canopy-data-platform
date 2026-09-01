"""Merge a bounded linked-car training sample with AI-Hub windows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def prepare(
    base_csv: str | Path,
    linked_csv: str | Path,
    output_csv: str | Path,
    manifest_json: str | Path,
    *,
    max_windows_per_user: int = 3,
) -> dict[str, object]:
    base = pd.read_csv(base_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    linked = pd.read_csv(linked_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    linked = linked[linked["split"].astype(str) == "train"].copy()
    linked = linked.sort_values(["user_id", "window_start", "trajectory_id"]).groupby("user_id", sort=False).head(max_windows_per_user)
    metadata_defaults = {
        "raw_point_count": 0,
        "missing_coordinate_count": 0,
        "invalid_coordinate_count": 0,
        "duplicate_timestamp_count": 0,
        "backwards_timestamp_count": 0,
        "gap_count": 0,
        "raw_label_values": "",
    }
    for column, default in metadata_defaults.items():
        linked[column] = default
    linked = linked[base.columns]
    combined = pd.concat([base, linked], ignore_index=True)
    destination = Path(output_csv)
    destination.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(destination, index=False, encoding="utf-8-sig")
    users = combined[["user_id", "split"]].drop_duplicates().sort_values("user_id")
    manifest = {
        "group_column": "user_id",
        "user_count": int(len(users)),
        "split_user_counts": {str(key): int(value) for key, value in users.groupby("split").size().items()},
        "groups": [{"user_id": str(row.user_id), "split": str(row.split)} for row in users.itertuples()],
        "augmentation": {"source": "AI-Hub linked vehicle archive", "max_windows_per_user": max_windows_per_user, "linked_rows": int(len(linked))},
    }
    manifest_path = Path(manifest_json)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"rows": int(len(combined)), "linked_rows": int(len(linked)), "user_count": int(len(users)), "split_user_counts": manifest["split_user_counts"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_csv", type=Path)
    parser.add_argument("linked_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("manifest_json", type=Path)
    parser.add_argument("--max-windows-per-user", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(prepare(args.base_csv, args.linked_csv, args.output_csv, args.manifest_json, max_windows_per_user=args.max_windows_per_user), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
