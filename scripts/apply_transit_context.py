"""Apply Transit Context evidence to a table containing ML probability columns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.pipeline import apply_resolver_to_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--source-kind", choices=("realtime", "reference", "geolife"), default="realtime")
    args = parser.parse_args()
    print(json.dumps(apply_resolver_to_csv(args.input_csv, args.output_csv, source_kind=args.source_kind), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
