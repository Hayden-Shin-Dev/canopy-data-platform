"""Compare canonical raw-120 AI-Hub candidates and save the validation winner."""

from __future__ import annotations

import argparse
import json

from src.aihub.selection import select_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical_csv")
    parser.add_argument("cadence_csv")
    parser.add_argument("split_manifest")
    parser.add_argument("model_output")
    parser.add_argument("report_output")
    parser.add_argument("--n-estimators", type=int, default=300)
    args = parser.parse_args()
    result = select_candidate(
        args.canonical_csv,
        args.cadence_csv,
        args.split_manifest,
        args.model_output,
        args.report_output,
        n_estimators=args.n_estimators,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
