"""Probe TAGO city-code access before fetching bus references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.api import load_transit_credentials
from src.transit_context.tago_api import fetch_tago_city_codes, probe_tago_services


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="data/cache/transit/tago_city_codes.json")
    parser.add_argument("--summary", default="data/processed/transit_context/tago_api_summary.json")
    parser.add_argument("--refresh-tago", action="store_true")
    args = parser.parse_args()
    credentials = load_transit_credentials()
    payload, summary = fetch_tago_city_codes(credentials["data_go_kr_service_key"], cache_path=args.cache, refresh=args.refresh_tago)
    summary["service_probes"] = probe_tago_services(credentials["data_go_kr_service_key"])
    if payload is not None:
        Path(args.cache).parent.mkdir(parents=True, exist_ok=True)
        Path(args.cache).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary.update({"cache_path": args.cache, "refresh": args.refresh_tago})
    output = Path(args.summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
