"""선택된 GeoLife 모델을 지정한 split에서 독립적으로 평가한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score


def evaluate_model(
    dataset_csv: str | Path,
    model_path: str | Path,
    *,
    split: str = "test",
) -> dict[str, object]:
    if split not in {"train", "validation", "test"}:
        raise ValueError("split은 train, validation, test 중 하나여야 합니다")
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    bundle = joblib.load(model_path)
    feature_columns = list(bundle["feature_columns"])
    classes = list(bundle["classes"])
    missing = sorted(set(feature_columns + ["canonical_mode", "split"]) - set(frame.columns))
    if missing:
        raise ValueError(f"평가 CSV에 필요한 column이 없습니다: {missing}")
    subset = frame[frame["split"] == split]
    if subset.empty:
        raise ValueError(f"평가 대상 split이 비어 있습니다: {split}")
    features = subset[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    predicted = bundle["model"].predict(features)
    return {
        "dataset_csv": str(dataset_csv),
        "model_path": str(model_path),
        "split": split,
        "row_count": len(subset),
        "user_count": int(subset["user_id"].nunique()),
        "accuracy": float(accuracy_score(subset["canonical_mode"], predicted)),
        "macro_f1": float(f1_score(subset["canonical_mode"], predicted, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(subset["canonical_mode"], predicted, average="weighted", zero_division=0)),
        "classes": classes,
        "classification_report": classification_report(
            subset["canonical_mode"], predicted, labels=classes, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(subset["canonical_mode"], predicted, labels=classes).tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("model_path")
    parser.add_argument("--split", default="test", choices=("train", "validation", "test"))
    parser.add_argument("--output")
    args = parser.parse_args()
    result = evaluate_model(args.dataset_csv, args.model_path, split=args.split)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
