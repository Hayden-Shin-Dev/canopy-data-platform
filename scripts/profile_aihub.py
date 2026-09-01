"""Profile an AI-Hub split without loading the full source into memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.aihub.ingest import profile_split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root")
    parser.add_argument("output_json")
    parser.add_argument("--split", choices=("Training", "Validation"), default="Training")
    parser.add_argument("--gap-threshold-seconds", type=float, default=120)
    args = parser.parse_args()
    result = profile_split(args.source_root, args.split, gap_threshold_seconds=args.gap_threshold_seconds)
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_root": str(args.source_root),
        "source_split": args.split,
        "gap_threshold_seconds": args.gap_threshold_seconds,
        **result.as_dict(),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
