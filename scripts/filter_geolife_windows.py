"""계산된 Window label purity 기준으로 Dataset을 재생성한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def filter_by_mode_purity(
    input_csv: str | Path,
    output_csv: str | Path,
    *,
    min_mode_purity: float | None = None,
) -> dict[str, object]:
    if min_mode_purity is not None and not 0 <= min_mode_purity <= 1:
        raise ValueError("min_mode_purity는 0 이상 1 이하여야 합니다")
    frame = pd.read_csv(input_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"canonical_mode_purity", "canonical_mode", "split", "user_id"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"purity filtering에 필요한 column이 없습니다: {missing}")
    if min_mode_purity is None:
        selected = frame
    else:
        selected = frame[frame["canonical_mode_purity"] >= min_mode_purity].copy()
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output, index=False, encoding="utf-8-sig")
    summary = {
        "input_csv": str(input_csv),
        "output_csv": str(output),
        "min_mode_purity": min_mode_purity,
        "input_window_count": len(frame),
        "selected_window_count": len(selected),
        "purity_rejected_count": len(frame) - len(selected),
        "mode_counts": selected["canonical_mode"].value_counts().sort_index().to_dict(),
        "split_counts": selected["split"].value_counts().sort_index().to_dict(),
        "user_count": int(selected["user_id"].nunique()),
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--min-mode-purity", type=float)
    args = parser.parse_args()
    print(
        json.dumps(
            filter_by_mode_purity(
                args.input_csv,
                args.output_csv,
                min_mode_purity=args.min_mode_purity,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
