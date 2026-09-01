"""Package a fixed legacy-plus-AI-Hub inference ensemble."""

from __future__ import annotations

import argparse
import joblib


def build(baseline_path: str, aihub_path: str, output_path: str, *, min_confidence: float = 0.6) -> None:
    baseline = joblib.load(baseline_path)
    aihub = joblib.load(aihub_path)
    if not isinstance(baseline, dict) or not isinstance(aihub, dict):
        raise ValueError("Both artifacts must be model bundles")
    if aihub.get("feature_version") != "aihub-window-v1":
        raise ValueError("AI-Hub artifact has an unexpected feature contract")
    joblib.dump(
        {
            "feature_version": "aihub-ensemble-v1",
            "window_duration_seconds": int(aihub.get("window_duration_seconds", 120)),
            "feature_columns": list(aihub["feature_columns"]),
            "classes": list(aihub["classes"]),
            "aihub_model": aihub["model"],
            "aihub_feature_columns": list(aihub["feature_columns"]),
            "aihub_classes": list(aihub["classes"]),
            "baseline_model": baseline["model"],
            "baseline_feature_columns": list(baseline["feature_columns"]),
            "baseline_classes": list(baseline["classes"]),
            "policy": "AI-Hub bus/rail only when legacy mode is not walk/bike",
            "min_aihub_confidence": float(min_confidence),
        },
        output_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_path")
    parser.add_argument("aihub_path")
    parser.add_argument("output_path")
    parser.add_argument("--min-confidence", type=float, default=0.6)
    args = parser.parse_args()
    build(args.baseline_path, args.aihub_path, args.output_path, min_confidence=args.min_confidence)


if __name__ == "__main__":
    main()
