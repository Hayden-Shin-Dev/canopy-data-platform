"""Create a user-disjoint AI-Hub split table and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.aihub.split import assign_user_splits, split_manifest


def assign_splits(input_csv: str | Path, output_csv: str | Path, manifest_path: str | Path, *, seed: int = 2021) -> dict[str, object]:
    frame = pd.read_csv(input_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    result = assign_user_splits(frame, seed=seed)
    output = Path(output_csv)
    manifest = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8-sig")
    summary = split_manifest(result)
    summary.update(
        {
            "seed": seed,
            "input_csv": str(input_csv),
            "output_csv": str(output),
            "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "row_counts": result["split"].value_counts().sort_index().astype(int).to_dict(),
        }
    )
    manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("manifest_json")
    parser.add_argument("--seed", type=int, default=2021)
    args = parser.parse_args()
    print(json.dumps(assign_splits(args.input_csv, args.output_csv, args.manifest_json, seed=args.seed), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
