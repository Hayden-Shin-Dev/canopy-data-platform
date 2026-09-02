"""Evaluate one frozen holdout under deterministic sampling-cadence changes."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .training import _biased_probabilities, _evaluate


def evaluate_cadence_stress(
    dataset_csv: str | Path,
    model_path: str | Path,
    output_json: str | Path,
    *,
    split: str = "test",
) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, encoding="utf-8-sig", dtype={"user_id": "string"})
    if "sampling_view" not in frame:
        raise ValueError("sampling_view is required for cadence stress evaluation")
    bundle = joblib.load(model_path)
    features = list(bundle["feature_columns"])
    classes = [str(value) for value in bundle["classes"]]
    holdout = frame[frame["split"] == split].copy()
    holdout["window_id"] = holdout["trajectory_id"].str.rsplit("__", n=1).str[0]
    native = holdout[holdout["sampling_view"] == "native"].copy()
    if native.empty:
        raise ValueError(f"native {split} rows are required")

    def predictions(subset: pd.DataFrame) -> tuple[list[str], np.ndarray]:
        probabilities = bundle["model"].predict_proba(subset[features])
        probabilities = _biased_probabilities(probabilities, classes, bundle.get("probability_bias"))
        predicted = [classes[index] for index in probabilities.argmax(axis=1)]
        return predicted, np.asarray(probabilities, dtype=float)

    native_predicted, native_probabilities = predictions(native)
    native_index = {window_id: index for index, window_id in enumerate(native["window_id"])}
    views: dict[str, object] = {}
    for view in sorted(holdout["sampling_view"].unique(), key=lambda value: (value != "native", value)):
        subset = holdout[holdout["sampling_view"] == view].copy()
        predicted, probabilities = predictions(subset)
        aligned = [
            (row_index, native_index[window_id])
            for row_index, window_id in enumerate(subset["window_id"])
            if window_id in native_index
        ]
        flip_rate = None
        probability_drift = None
        if aligned:
            flips = [predicted[row_index] != native_predicted[native_row] for row_index, native_row in aligned]
            drifts = [
                float(np.abs(probabilities[row_index] - native_probabilities[native_row]).sum() / 2)
                for row_index, native_row in aligned
            ]
            flip_rate = float(np.mean(flips))
            probability_drift = float(np.mean(drifts))
        views[str(view)] = {
            "metrics": _evaluate(bundle["model"], subset, features, probability_bias=bundle.get("probability_bias")),
            "usable_window_coverage": len(subset) / len(native),
            "aligned_window_count": len(aligned),
            "prediction_flip_rate_vs_native": flip_rate,
            "mean_probability_total_variation_vs_native": probability_drift,
        }
    result = {
        "status": "PASS",
        "split": split,
        "model": str(model_path),
        "native_window_count": int(len(native)),
        "views": views,
    }
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
