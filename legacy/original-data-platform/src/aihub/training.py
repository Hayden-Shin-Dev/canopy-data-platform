"""Model training and evaluation for an AI-Hub window table."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, log_loss

from .config import CANOPY_MODES
from .features import AIHUB_FEATURE_COLUMNS


BASE_FEATURE_COLUMNS = AIHUB_FEATURE_COLUMNS[:16]
ROBUST_FEATURE_COLUMNS = tuple(
    column for column in AIHUB_FEATURE_COLUMNS
    if column not in {"point_count", "observed_duration_sec", "avg_sampling_interval_sec", "valid_step_count", "gap_step_count"}
)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _multiclass_brier_score(target: pd.Series, probabilities: Any, classes: list[str]) -> float:
    """Average squared error of the complete class probability vector."""
    class_index = {name: index for index, name in enumerate(classes)}
    score = 0.0
    for label, row in zip(target.astype(str), probabilities):
        expected = [0.0] * len(classes)
        if label in class_index:
            expected[class_index[label]] = 1.0
        score += sum((float(value) - expected[index]) ** 2 for index, value in enumerate(row))
    return score / max(len(target), 1)


def make_model(model_type: str, *, seed: int = 2021, n_estimators: int = 300, class_weight: str | None = "balanced") -> Any:
    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=n_estimators,
            class_weight="balanced_subsample" if class_weight else None,
            random_state=seed,
            n_jobs=-1,
        )
    if model_type == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=n_estimators,
            class_weight=class_weight,
            random_state=seed,
            n_jobs=-1,
        )
    if model_type == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.08,
            max_leaf_nodes=31,
            class_weight=class_weight,
            random_state=seed,
        )
    if model_type == "catboost":
        try:
            from catboost import CatBoostClassifier
        except ImportError as error:
            raise RuntimeError("CatBoost is not installed") from error
        return CatBoostClassifier(
            iterations=400,
            depth=8,
            learning_rate=0.08,
            loss_function="MultiClass",
            auto_class_weights="Balanced" if class_weight else None,
            random_seed=seed,
            verbose=False,
            thread_count=-1,
        )
    raise ValueError(f"Unsupported AI-Hub model type: {model_type}")


def _biased_probabilities(probabilities: Any, classes: Sequence[str], bias: Sequence[float] | None) -> Any:
    """Apply validation-only class logit offsets without changing feature extraction."""
    if bias is None:
        return probabilities
    import numpy as np

    values = np.asarray(probabilities, dtype=float)
    offsets = np.asarray(list(bias), dtype=float)
    if values.ndim != 2 or offsets.shape != (values.shape[1],):
        raise ValueError("probability bias must contain one value per model class")
    logits = np.log(np.clip(values, 1e-12, 1.0)) + offsets
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def _evaluate(
    model: Any,
    frame: pd.DataFrame,
    features: list[str],
    *,
    probability_bias: Sequence[float] | None = None,
) -> dict[str, object]:
    target = frame["canonical_mode"].astype(str)
    probabilities = model.predict_proba(frame[features])
    model_classes = [str(value) for value in getattr(model, "classes_", CANOPY_MODES)]
    probabilities = _biased_probabilities(probabilities, model_classes, probability_bias)
    predicted = [model_classes[index] for index in probabilities.argmax(axis=1)]
    report = classification_report(
        target,
        predicted,
        labels=list(CANOPY_MODES),
        output_dict=True,
        zero_division=0,
    )
    return {
        "row_count": int(len(frame)),
        "accuracy": float(accuracy_score(target, predicted)),
        "macro_f1": float(f1_score(target, predicted, labels=list(CANOPY_MODES), average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(target, predicted, labels=list(CANOPY_MODES), average="weighted", zero_division=0)),
        "log_loss": float(log_loss(target, probabilities, labels=model_classes)),
        "brier_score": _multiclass_brier_score(target, probabilities, model_classes),
        "classification_report": report,
        "confusion_matrix_labels": list(CANOPY_MODES),
        "confusion_matrix": confusion_matrix(target, predicted, labels=list(CANOPY_MODES)).tolist(),
    }


def _calibrate_probability_bias(
    model: Any,
    frame: pd.DataFrame,
    features: list[str],
    *,
    classes: Sequence[str],
) -> list[float]:
    """Select small class offsets on validation only, maximizing macro F1.

    The offsets are part of the model contract and are applied to every future
    window. Test rows are never inspected while selecting them.
    """
    import numpy as np

    target = frame["canonical_mode"].astype(str)
    probabilities = model.predict_proba(frame[features])
    class_index = {name: index for index, name in enumerate(classes)}
    labels = list(CANOPY_MODES)

    def score(offsets: np.ndarray) -> float:
        adjusted = _biased_probabilities(probabilities, classes, offsets)
        predicted = [classes[index] for index in adjusted.argmax(axis=1)]
        return float(f1_score(target, predicted, labels=labels, average="macro", zero_division=0))

    best = np.zeros(len(classes), dtype=float)
    best_score = score(best)
    # Coarse-to-fine coordinate ascent keeps calibration deterministic and
    # small enough to reproduce in a local rebuild.
    for step, radius in ((0.05, 0.4), (0.025, 0.1)):
        for index in range(len(classes)):
            candidates = np.arange(best[index] - radius, best[index] + radius + step / 2, step)
            for value in candidates:
                candidate = best.copy()
                candidate[index] = float(value)
                candidate_score = score(candidate)
                if candidate_score > best_score + 1e-10:
                    best, best_score = candidate, candidate_score
    return [round(float(value), 6) for value in best]


def train_model(
    dataset_csv: str | Path,
    model_path: str | Path,
    metrics_path: str | Path,
    *,
    model_type: str = "extra_trees",
    seed: int = 2021,
    n_estimators: int = 300,
    class_weight: str | None = "balanced",
    feature_set: str = "all",
    split_manifest_path: str | Path | None = None,
    window_seconds: int = 60,
    calibrate_validation: bool = False,
) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"user_id", "canonical_mode", "split", *AIHUB_FEATURE_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"AI-Hub training table is missing columns: {missing}")
    if feature_set not in {"all", "base", "robust"}:
        raise ValueError("feature_set must be all, base, or robust")
    feature_columns = list({"all": AIHUB_FEATURE_COLUMNS, "base": BASE_FEATURE_COLUMNS, "robust": ROBUST_FEATURE_COLUMNS}[feature_set])
    for column in feature_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    test = frame[frame["split"] == "test"]
    if train.empty or validation.empty or test.empty:
        raise ValueError("train, validation, and test rows are all required")
    for split_name, subset in (("train", train), ("validation", validation), ("test", test)):
        missing_classes = sorted(set(CANOPY_MODES) - set(subset["canonical_mode"].astype(str)))
        if missing_classes:
            raise ValueError(f"{split_name} split is missing classes: {missing_classes}")
    model = make_model(model_type, seed=seed, n_estimators=n_estimators, class_weight=class_weight)
    model.fit(train[feature_columns], train["canonical_mode"])
    model_classes = [str(value) for value in getattr(model, "classes_", CANOPY_MODES)]
    probability_bias = (
        _calibrate_probability_bias(model, validation, feature_columns, classes=model_classes)
        if calibrate_validation
        else None
    )
    result: dict[str, object] = {
        "model_type": model_type,
        "seed": seed,
        "n_estimators": n_estimators,
        "class_weight": class_weight,
        "feature_set": feature_set,
        "feature_version": "aihub-window-v1",
        "window_duration_seconds": int(window_seconds),
        "probability_bias": probability_bias,
        "feature_columns": feature_columns,
        "classes": model_classes,
        "dataset_sha256": _sha256(dataset_csv),
        "split_manifest_sha256": _sha256(split_manifest_path) if split_manifest_path else None,
        "metrics": {
            "train": _evaluate(model, train, feature_columns, probability_bias=probability_bias),
            "validation": _evaluate(model, validation, feature_columns, probability_bias=probability_bias),
            "test": _evaluate(model, test, feature_columns, probability_bias=probability_bias),
        },
    }
    model_output = Path(model_path)
    metrics_output = Path(metrics_path)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "classes": model_classes,
            "dataset_sha256": result["dataset_sha256"],
            "split_manifest_sha256": result["split_manifest_sha256"],
            "feature_version": "aihub-window-v1",
            "window_duration_seconds": int(window_seconds),
            "probability_bias": probability_bias,
        },
        model_output,
    )
    metrics_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
