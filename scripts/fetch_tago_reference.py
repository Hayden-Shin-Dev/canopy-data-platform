"""Probe TAGO city-code access before fetching bus references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.api import TransitApiClient, load_transit_credentials
from src.transit_context.bus_reference import build_bus_reference_files
from src.transit_context.tago_api import TAGO_SAMPLE_SCOPE, TAGO_SERVICE_ENDPOINTS, fetch_tago_city_codes, parse_tago_bus_stops, parse_tago_route_stops, probe_tago_services


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="data/cache/transit/tago_city_codes.json")
    parser.add_argument("--summary", default="data/processed/transit_context/tago_api_summary.json")
    parser.add_argument("--national-bus-stops", help="official national bus stop coordinate CSV")
    parser.add_argument("--refresh-tago", action="store_true")
    args = parser.parse_args()
    credentials = load_transit_credentials()
    payload, summary = fetch_tago_city_codes(credentials["data_go_kr_service_key"], cache_path=args.cache, refresh=args.refresh_tago)
    summary["service_probes"] = probe_tago_services(credentials["data_go_kr_service_key"])
    if payload is not None:
        Path(args.cache).parent.mkdir(parents=True, exist_ok=True)
        Path(args.cache).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if summary["status"] == "success":
        client = TransitApiClient()
        key = unquote(credentials["data_go_kr_service_key"] or "")
        query = {"serviceKey": key, "pageNo": 1, "numOfRows": 1000, "dataType": "JSON", **TAGO_SAMPLE_SCOPE}
        parsed_tables = {}
        for name, parser, output_name in (("bus_stops", parse_tago_bus_stops, "bus_stops.csv"), ("bus_routes", parse_tago_route_stops, "bus_route_stops.csv")):
            try:
                pages = []
                page_number = 1
                while True:
                    page_query = {**query, "pageNo": page_number}
                    response = client.fetch_json(TAGO_SERVICE_ENDPOINTS[name], params=page_query, cache_path=f"data/cache/transit/{name}_sample_page{page_number}.json", refresh=args.refresh_tago)
                    page = parser(response.payload)
                    pages.append(page)
                    if len(page) < 1000:
                        break
                    page_number += 1
                import pandas as pd
                parsed = pd.concat(pages, ignore_index=True).drop_duplicates().reset_index(drop=True)
                parsed_tables[name] = parsed
                summary[f"{name}_sample"] = {"status": "success", "rows": len(parsed), "pages": page_number, "coordinate_status": "not_provided_by_api", "scope": TAGO_SAMPLE_SCOPE}
            except Exception as exc:
                summary[f"{name}_sample"] = {"status": "error", "error_type": type(exc).__name__, "error": str(exc)}
        if set(parsed_tables) == {"bus_stops", "bus_routes"}:
            national_path = Path(args.national_bus_stops) if args.national_bus_stops else None
            if national_path is None:
                candidates = sorted(Path("data/raw/transit").glob("*\ubc84\uc2a4\uc815\ub958\uc7a5*"))
                national_path = candidates[0] if candidates else None
            if national_path is not None and national_path.exists():
                bus_summary = build_bus_reference_files(parsed_tables["bus_stops"], parsed_tables["bus_routes"], national_path, "data/processed/transit_context")
                summary["national_bus_stop_file"] = str(national_path)
                summary["bus_coordinate_match"] = bus_summary
            else:
                output_dir = Path("data/processed/transit_context")
                output_dir.mkdir(parents=True, exist_ok=True)
                parsed_tables["bus_stops"].to_csv(output_dir / "bus_stops.csv", index=False, encoding="utf-8-sig")
                parsed_tables["bus_routes"].to_csv(output_dir / "bus_route_stops.csv", index=False, encoding="utf-8-sig")
                summary["bus_coordinate_match"] = {"status": "not_run", "reason": "national bus stop coordinate file was not supplied"}
    summary.update({"cache_path": args.cache, "refresh": args.refresh_tago})
    output = Path(args.summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
