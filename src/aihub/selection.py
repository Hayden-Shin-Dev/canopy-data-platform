"""Validation-only candidate selection for the canonical AI-Hub runtime contract."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .config import CANOPY_MODES
from .features import AIHUB_FEATURE_COLUMNS
from .training import ROBUST_FEATURE_COLUMNS, _evaluate, make_model


CANDIDATES = (
    ("c1_hgb_all", "hist_gradient_boosting", "all", False, None),
    ("c2_hgb_robust", "hist_gradient_boosting", "robust", False, "balanced"),
    ("c2_extra_trees_robust", "extra_trees", "robust", False, "balanced"),
    ("c2_random_forest_robust", "random_forest", "robust", False, "balanced"),
    ("c3_hgb_robust_cadence", "hist_gradient_boosting", "robust", True, "balanced"),
    ("c3_extra_trees_robust_cadence", "extra_trees", "robust", True, "balanced"),
    ("c3_random_forest_robust_cadence", "random_forest", "robust", True, "balanced"),
)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype={"user_id": "string"})
    required = {"user_id", "canonical_mode", "split", *AIHUB_FEATURE_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"AI-Hub candidate table is missing columns: {missing}")
    for column in AIHUB_FEATURE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    return frame


def _validate_split(frame: pd.DataFrame) -> dict[str, object]:
    users = {
        split: set(frame.loc[frame["split"] == split, "user_id"].astype(str))
        for split in ("train", "validation", "test")
    }
    overlap = {
        "train_validation": len(users["train"] & users["validation"]),
        "train_test": len(users["train"] & users["test"]),
        "validation_test": len(users["validation"] & users["test"]),
    }
    if any(overlap.values()):
        raise ValueError(f"UID split overlap detected: {overlap}")
    for split in users:
        modes = set(frame.loc[frame["split"] == split, "canonical_mode"].astype(str))
        if set(CANOPY_MODES) - modes:
            raise ValueError(f"{split} is missing modes: {sorted(set(CANOPY_MODES) - modes)}")
    return {"user_counts": {key: len(value) for key, value in users.items()}, "overlap": overlap}


def select_candidate(
    canonical_csv: str | Path,
    cadence_csv: str | Path,
    split_manifest: str | Path,
    model_output: str | Path,
    report_output: str | Path,
    *,
    seed: int = 2021,
    n_estimators: int = 300,
) -> dict[str, object]:
    canonical = _load(canonical_csv)
    cadence = _load(cadence_csv)
    split_audit = _validate_split(canonical)
    cadence_audit = _validate_split(cadence)
    # Validation/Test는 두 표에서 동일한 native rows여야 한다.
    for split in ("validation", "test"):
        left = canonical[canonical["split"] == split].reset_index(drop=True)
        right = cadence[cadence["split"] == split].reset_index(drop=True)
        if not left.equals(right[left.columns]):
            raise ValueError(f"{split} changed in cadence augmentation")

    results: list[dict[str, object]] = []
    best: tuple[float, Any, dict[str, object], pd.DataFrame, list[str]] | None = None
    for name, model_type, feature_set, use_cadence, class_weight in CANDIDATES:
        frame = cadence if use_cadence else canonical
        features = list(AIHUB_FEATURE_COLUMNS if feature_set == "all" else ROBUST_FEATURE_COLUMNS)
        train = frame[frame["split"] == "train"]
        validation = frame[frame["split"] == "validation"]
        model = make_model(
            model_type,
            seed=seed,
            n_estimators=n_estimators,
            class_weight=class_weight,
        )
        model.fit(train[features], train["canonical_mode"])
        validation_metrics = _evaluate(model, validation, features)
        record = {
            "name": name,
            "model_type": model_type,
            "feature_set": feature_set,
            "cadence_augmented_train": use_cadence,
            "class_weight": class_weight,
            "train_rows": int(len(train)),
            "validation": validation_metrics,
        }
        results.append(record)
        score = float(validation_metrics["macro_f1"])
        if best is None or score > best[0]:
            best = (score, model, record, frame, features)
        else:
            del model
            gc.collect()

    assert best is not None
    _, model, selected, selected_frame, features = best
    test = canonical[canonical["split"] == "test"]
    final_metrics = {
        "validation": selected["validation"],
        "test": _evaluate(model, test, features),
    }
    classes = [str(value) for value in model.classes_]
    artifact = {
        "model": model,
        "feature_columns": features,
        "classes": classes,
        "feature_version": "aihub-canonical-raw120-v2",
        "window_duration_seconds": 120,
        "runtime_stride_seconds": 10,
        "dataset_sha256": _sha256(cadence_csv if selected["cadence_augmented_train"] else canonical_csv),
        "split_manifest_sha256": _sha256(split_manifest),
        "selected_candidate": selected["name"],
        "selection_metric": "validation_macro_f1",
    }
    model_path = Path(model_output)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    report = {
        "status": "PASS",
        "selection_policy": "UID-disjoint validation Macro F1; test evaluated once for selected candidate",
        "canonical_dataset_sha256": _sha256(canonical_csv),
        "cadence_dataset_sha256": _sha256(cadence_csv),
        "split_manifest_sha256": _sha256(split_manifest),
        "split_audit": split_audit,
        "cadence_split_audit": cadence_audit,
        "candidates": results,
        "selected_candidate": selected["name"],
        "selected_metrics": final_metrics,
        "model_output": str(model_path),
    }
    report_path = Path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
