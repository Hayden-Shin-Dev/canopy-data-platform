"""Merge AI-Hub Training and Validation feature tables into one pool."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def merge_tables(training_csv: str | Path, validation_csv: str | Path, output_csv: str | Path) -> dict[str, object]:
    training = pd.read_csv(training_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    validation = pd.read_csv(validation_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"user_id", "trajectory_id", "canonical_mode"}
    for name, frame in (("training", training), ("validation", validation)):
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{name} table is missing columns: {missing}")
    pool = pd.concat([training, validation], ignore_index=True)
    if pool["trajectory_id"].duplicated().any():
        raise ValueError("Duplicate trajectory_id found while merging AI-Hub tables")
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(output, index=False, encoding="utf-8-sig")
    return {
        "training_rows": int(len(training)),
        "validation_rows": int(len(validation)),
        "pool_rows": int(len(pool)),
        "output_csv": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_csv")
    parser.add_argument("validation_csv")
    parser.add_argument("output_csv")
    args = parser.parse_args()
    print(merge_tables(args.training_csv, args.validation_csv, args.output_csv))


if __name__ == "__main__":
    main()
