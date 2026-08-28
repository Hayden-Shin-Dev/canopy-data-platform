"""GeoLife Window CSV에 user 기준 split을 추가한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.geolife.split import apply_group_split_map, assign_group_splits


def assign_splits(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    seed: int = 2021,
    reference_split_csv: str | Path | None = None,
) -> dict[str, object]:
    frame = pd.read_csv(input_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    if reference_split_csv is None:
        result = assign_group_splits(frame, seed=seed)
    else:
        reference = pd.read_csv(reference_split_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
        required = {"user_id", "split"}
        missing = sorted(required - set(reference.columns))
        if missing:
            raise ValueError(f"reference split CSV에 필요한 column이 없습니다: {missing}")
        split_map = (
            reference[["user_id", "split"]]
            .drop_duplicates()
            .set_index("user_id")["split"]
            .to_dict()
        )
        result = apply_group_split_map(frame, split_map)
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    groups_by_split = {
        split: sorted(result.loc[result["split"] == split, "user_id"].astype(str).unique().tolist())
        for split in ("train", "validation", "test")
    }
    summary = {
        "input_csv": str(input_csv),
        "output_csv": str(output_path),
        "seed": seed,
        "row_counts": result["split"].value_counts().sort_index().to_dict(),
        "user_counts": {split: len(users) for split, users in groups_by_split.items()},
        "users": groups_by_split,
        "mode_counts": {
            split: result.loc[result["split"] == split, "canonical_mode"].value_counts().sort_index().to_dict()
            for split in ("train", "validation", "test")
        },
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--seed", type=int, default=2021)
    parser.add_argument("--reference-split-csv", help="기존 user split을 재사용할 CSV 경로")
    args = parser.parse_args()
    print(
        json.dumps(
            assign_splits(
                args.input_csv,
                args.output_csv,
                seed=args.seed,
                reference_split_csv=args.reference_split_csv,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
