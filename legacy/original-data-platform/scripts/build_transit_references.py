"""Create normalized Transit Context rail references from supplied CSV files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.references import build_reference_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subway-coordinates", required=True)
    parser.add_argument("--subway-timetable", required=True)
    parser.add_argument("--korail-stations", required=True)
    parser.add_argument("--output-dir", default="data/processed/transit_context")
    args = parser.parse_args()
    result = build_reference_files(
        output_dir=args.output_dir,
        subway_coordinates=args.subway_coordinates,
        subway_timetable=args.subway_timetable,
        korail_stations=args.korail_stations,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
