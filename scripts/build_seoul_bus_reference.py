"""Build Seoul bus stop and ordered route-stop references from the official workbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.seoul_bus_reference import build_seoul_bus_reference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="서울시버스노선별정류소정보 workbook")
    parser.add_argument("--output-dir", default="data/processed/transit_context")
    args = parser.parse_args()
    print(json.dumps(build_seoul_bus_reference(args.source, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
