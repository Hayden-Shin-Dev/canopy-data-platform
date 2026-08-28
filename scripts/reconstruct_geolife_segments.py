"""Window 예측을 user/trajectory별 연속 mode segment로 재구성한다."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd

from src.geolife.segments import merge_consecutive_predictions


def reconstruct_segments(
    dataset_csv: str | Path,
    model_path: str | Path,
    output_csv: str | Path,
    *,
    split: str = "test",
) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    bundle = joblib.load(model_path)
    required = set(bundle["feature_columns"]) | {"user_id", "trajectory_id", "window_start", "canonical_mode", "split"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"segment 재구성 CSV에 필요한 column이 없습니다: {missing}")
    frame = frame[frame["split"] == split].copy()
    if frame.empty:
        raise ValueError(f"segment 재구성 대상 split이 비어 있습니다: {split}")
    frame["_window_start"] = pd.to_datetime(frame["window_start"], errors="raise")
    features = frame[list(bundle["feature_columns"])].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    frame["predicted_mode"] = bundle["model"].predict(features)
    frame.sort_values(["user_id", "trajectory_id", "_window_start"], inplace=True)

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["user_id", "trajectory_id", "segment_index", "start_index", "end_index", "window_count", "predicted_mode"]
    segment_count = 0
    mode_counts: Counter[str] = Counter()
    trajectory_count = 0
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for (user_id, trajectory_id), group in frame.groupby(["user_id", "trajectory_id"], sort=False):
            trajectory_count += 1
            segments = merge_consecutive_predictions(group["predicted_mode"].tolist())
            for segment_index, segment in enumerate(segments):
                writer.writerow(
                    {
                        "user_id": str(user_id),
                        "trajectory_id": trajectory_id,
                        "segment_index": segment_index,
                        "start_index": segment.start_index,
                        "end_index": segment.end_index,
                        "window_count": segment.window_count,
                        "predicted_mode": segment.mode,
                    }
                )
                segment_count += 1
                mode_counts[segment.mode] += 1

    summary = {
        "dataset_csv": str(dataset_csv),
        "model_path": str(model_path),
        "output_csv": str(output_path),
        "split": split,
        "trajectory_count": trajectory_count,
        "window_count": len(frame),
        "segment_count": segment_count,
        "predicted_segment_mode_counts": dict(sorted(mode_counts.items())),
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("model_path")
    parser.add_argument("output_csv")
    parser.add_argument("--split", default="test", choices=("train", "validation", "test"))
    args = parser.parse_args()
    print(json.dumps(reconstruct_segments(args.dataset_csv, args.model_path, args.output_csv, split=args.split), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
