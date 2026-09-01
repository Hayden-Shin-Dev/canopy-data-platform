"""Train one AI-Hub model candidate and write its artifact and metrics."""

from __future__ import annotations

import argparse
import json

from src.aihub.training import train_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("model_path")
    parser.add_argument("metrics_json")
    parser.add_argument("--model-type", choices=("random_forest", "extra_trees", "hist_gradient_boosting", "catboost"), default="extra_trees")
    parser.add_argument("--seed", type=int, default=2021)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--class-weight", choices=("balanced", "none"), default="balanced")
    parser.add_argument("--feature-set", choices=("all", "base", "robust"), default="all")
    parser.add_argument("--split-manifest", default=None, help="Optional split manifest whose hash is recorded in the artifact")
    parser.add_argument("--window-seconds", type=int, default=60)
    parser.add_argument(
        "--calibrate-validation",
        action="store_true",
        help="fit deterministic class probability offsets on validation Macro F1 only",
    )
    args = parser.parse_args()
    result = train_model(
        args.dataset_csv,
        args.model_path,
        args.metrics_json,
        model_type=args.model_type,
        seed=args.seed,
        n_estimators=args.n_estimators,
        class_weight=None if args.class_weight == "none" else args.class_weight,
        feature_set=args.feature_set,
        split_manifest_path=args.split_manifest,
        window_seconds=args.window_seconds,
        calibrate_validation=args.calibrate_validation,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
