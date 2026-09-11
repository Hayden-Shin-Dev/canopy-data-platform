"""Join Seoul station-line metadata to supplied station coordinates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.normalization import normalize_subway_stations
from src.transit_context.seoul_api import merge_line_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinates", required=True)
    parser.add_argument("--api-lines", default="data/processed/transit_context/seoul_station_lines.csv")
    parser.add_argument("--output", default="data/processed/transit_context/subway_station_line_enrichment.csv")
    parser.add_argument("--unmatched", default="data/processed/transit_context/seoul_station_unmatched.csv")
    args = parser.parse_args()
    coordinates = normalize_subway_stations(args.coordinates)
    import pandas as pd
    api_lines = pd.read_csv(args.api_lines, encoding="utf-8-sig")
    matched, unmatched = merge_line_metadata(coordinates, api_lines)
    output, unmatched_path = Path(args.output), Path(args.unmatched)
    output.parent.mkdir(parents=True, exist_ok=True)
    matched.to_csv(output, index=False, encoding="utf-8-sig")
    unmatched.to_csv(unmatched_path, index=False, encoding="utf-8-sig")
    print(json.dumps({"matched_rows": len(matched), "unmatched_rows": len(unmatched), "output": str(output), "unmatched": str(unmatched_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
