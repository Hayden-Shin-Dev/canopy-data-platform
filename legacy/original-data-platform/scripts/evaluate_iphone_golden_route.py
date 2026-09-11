"""Evaluate local iPhone prediction JSONL against separately annotated segments."""

from __future__ import annotations

import argparse
import json

from src.aihub.iphone_evaluation import evaluate_iphone_journey


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions_jsonl")
    parser.add_argument("manual_segments_csv")
    parser.add_argument("output_json")
    args = parser.parse_args()
    print(json.dumps(evaluate_iphone_journey(args.predictions_jsonl, args.manual_segments_csv, args.output_json), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
