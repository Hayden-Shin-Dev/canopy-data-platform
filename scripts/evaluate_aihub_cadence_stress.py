"""Run sampling-cadence stress evaluation on a frozen AI-Hub holdout."""

from __future__ import annotations

import argparse
import json

from src.aihub.cadence_stress import evaluate_cadence_stress


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("model_path")
    parser.add_argument("output_json")
    parser.add_argument("--split", default="test", choices=("validation", "test"))
    args = parser.parse_args()
    print(json.dumps(evaluate_cadence_stress(args.dataset_csv, args.model_path, args.output_json, split=args.split), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
