"""Evaluate Movement, Temporal, Transit and Final modes on an AI-Hub UID split."""

from __future__ import annotations

import argparse
import json

from src.aihub.stage_evaluation import evaluate_stages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root")
    parser.add_argument("split_manifest")
    parser.add_argument("model_path")
    parser.add_argument("output_json")
    parser.add_argument("--split", default="test", choices=("validation", "test"))
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--reference-dir")
    args = parser.parse_args()
    result = evaluate_stages(
        args.source_root,
        args.split_manifest,
        args.model_path,
        args.output_json,
        split=args.split,
        workers=args.workers,
        reference_dir=args.reference_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
