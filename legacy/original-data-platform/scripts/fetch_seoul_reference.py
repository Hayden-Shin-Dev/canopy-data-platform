"""Fetch and cache the observed Seoul subway station-line reference."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.api import load_transit_credentials
from src.transit_context.seoul_api import fetch_seoul_station_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="data/cache/transit/seoul_station_lines.json")
    parser.add_argument("--output", default="data/processed/transit_context/seoul_station_lines.csv")
    parser.add_argument("--refresh-seoul", action="store_true")
    args = parser.parse_args()
    credentials = load_transit_credentials()
    frame, metadata = fetch_seoul_station_lines(credentials["seoul_openapi_key"], cache_path=args.cache, refresh=args.refresh_seoul)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, encoding="utf-8-sig")
    metadata.update({"cache_path": str(args.cache), "output_csv": str(output), "refresh": args.refresh_seoul})
    output.with_name("seoul_api_summary.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
