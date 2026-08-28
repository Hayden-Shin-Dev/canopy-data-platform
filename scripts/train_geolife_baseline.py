"""GeoLife Window Feature로 사용자 기준 split baseline을 학습한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


TARGET_COLUMN = "canonical_mode"
METADATA_COLUMNS = {
    "user_id",
    "trajectory_id",
    "window_start",
    "window_end",
    TARGET_COLUMN,
    "split",
    "label_coverage",
    "matched_point_count",
    "ambiguous_point_count",
    "excluded_point_count",
}
EXPECTED_CLASSES = ("walk", "bike", "car", "bus", "rail")


def train_baseline(
    dataset_csv: str | Path,
    model_path: str | Path,
    metrics_path: str | Path,
    *,
    n_estimators: int = 100,
    random_seed: int = 2021,
    class_weight: str | None = "balanced_subsample",
    model_type: str = "random_forest",
) -> dict[str, object]:
    if n_estimators < 1:
        raise ValueError("n_estimators는 양수여야 합니다")
    if class_weight not in (None, "balanced", "balanced_subsample"):
        raise ValueError("class_weight는 None, balanced, balanced_subsample 중 하나여야 합니다")
    if model_type not in ("random_forest", "extra_trees"):
        raise ValueError("model_type은 random_forest 또는 extra_trees여야 합니다")
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = METADATA_COLUMNS | {"split"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"학습 CSV에 필요한 column이 없습니다: {missing}")
    feature_columns = [column for column in frame.columns if column not in METADATA_COLUMNS]
    if not feature_columns:
        raise ValueError("학습에 사용할 numeric feature가 없습니다")
    for column in feature_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)

    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    test = frame[frame["split"] == "test"]
    if train.empty or validation.empty or test.empty:
        raise ValueError("train, validation, test split이 모두 필요합니다")
    missing_classes = sorted(set(EXPECTED_CLASSES) - set(train[TARGET_COLUMN]))
    if missing_classes:
        raise ValueError(f"train split에 없는 target class가 있습니다: {missing_classes}")

    classifier = RandomForestClassifier if model_type == "random_forest" else ExtraTreesClassifier
    model = classifier(
        n_estimators=n_estimators,
        random_state=random_seed,
        n_jobs=-1,
        class_weight=class_weight,
    )
    model.fit(train[feature_columns], train[TARGET_COLUMN])
    classes = list(model.classes_)

    def evaluate(subset: pd.DataFrame) -> dict[str, object]:
        predicted = model.predict(subset[feature_columns])
        report = classification_report(
            subset[TARGET_COLUMN],
            predicted,
            labels=classes,
            output_dict=True,
            zero_division=0,
        )
        return {
            "row_count": len(subset),
            "accuracy": float(accuracy_score(subset[TARGET_COLUMN], predicted)),
            "macro_f1": float(f1_score(subset[TARGET_COLUMN], predicted, average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(subset[TARGET_COLUMN], predicted, average="weighted", zero_division=0)),
            "classification_report": report,
            "confusion_matrix": confusion_matrix(subset[TARGET_COLUMN], predicted, labels=classes).tolist(),
        }

    result = {
        "model": type(model).__name__,
        "n_estimators": n_estimators,
        "random_seed": random_seed,
        "class_weight": class_weight,
        "feature_columns": feature_columns,
        "classes": classes,
        "split_users": {
            split: sorted(frame.loc[frame["split"] == split, "user_id"].astype(str).unique().tolist())
            for split in ("train", "validation", "test")
        },
        "metrics": {
            "train": evaluate(train),
            "validation": evaluate(validation),
            "test": evaluate(test),
        },
    }
    model_output = Path(model_path)
    metrics_output = Path(metrics_path)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_columns, "classes": classes}, model_output)
    metrics_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("model_path")
    parser.add_argument("metrics_path")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=2021)
    parser.add_argument("--class-weight", choices=("none", "balanced", "balanced_subsample"), default="balanced_subsample")
    parser.add_argument("--model-type", choices=("random_forest", "extra_trees"), default="random_forest")
    args = parser.parse_args()
    result = train_baseline(
        args.dataset_csv,
        args.model_path,
        args.metrics_path,
        n_estimators=args.n_estimators,
        random_seed=args.random_seed,
        class_weight=None if args.class_weight == "none" else args.class_weight,
        model_type=args.model_type,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
