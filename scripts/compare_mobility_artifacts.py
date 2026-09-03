"""Compare existing mobility artifacts on the same canonical UID holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from src.aihub.training import _evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("output_json")
    parser.add_argument("--model", action="append", required=True, help="name=artifact_path")
    args = parser.parse_args()
    frame = pd.read_csv(args.dataset_csv, encoding="utf-8-sig")
    result = {
        "dataset": args.dataset_csv,
        "comparison_contract": "same canonical raw-120 UID-disjoint validation/test rows",
        "models": {},
    }
    for item in args.model:
        name, separator, raw_path = item.partition("=")
        if not separator:
            parser.error("--model must use name=artifact_path")
        bundle = joblib.load(raw_path)
        features = list(bundle["feature_columns"])
        result["models"][name] = {
            "artifact": raw_path,
            "feature_version": bundle.get("feature_version", "legacy-geolife"),
            "validation": _evaluate(bundle["model"], frame[frame["split"] == "validation"], features, probability_bias=bundle.get("probability_bias")),
            "test": _evaluate(bundle["model"], frame[frame["split"] == "test"], features, probability_bias=bundle.get("probability_bias")),
        }
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
