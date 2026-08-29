"""Validate Transit Context references and write an honest API readiness report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transit_context.api import load_transit_credentials


API_ENDPOINT_CONFIG = PROJECT_ROOT / "config" / "transit_api_endpoints.json"


def _table_stats(path: Path, required: set[str]) -> dict[str, object]:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    coords = all(frame[column].between(-90, 90).all() for column in ["latitude"] if column in frame)
    if "longitude" in frame:
        coords = coords and frame["longitude"].between(-180, 180).all()
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "missing_required_columns": sorted(required - set(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "invalid_coordinate_rows": int((~frame[["latitude", "longitude"]].apply(pd.to_numeric, errors="coerce").apply(lambda col: col.between(-90, 90) if col.name == "latitude" else col.between(-180, 180)).all(axis=1)).sum()) if {"latitude", "longitude"} <= set(frame.columns) else None,
        "coordinates_valid": bool(coords),
    }


def validate(reference_dir: str | Path, report_dir: str | Path) -> dict[str, object]:
    references = Path(reference_dir)
    reports = Path(report_dir)
    reports.mkdir(parents=True, exist_ok=True)
    tables = {
        "subway_stations": _table_stats(references / "subway_stations.csv", {"station_id", "station_name", "normalized_station_name", "line", "latitude", "longitude", "source"}),
        "subway_timetable": _table_stats(references / "subway_timetable.csv", {"line", "station_id", "station_name", "direction", "service_type", "arrival_time", "departure_time"}),
        "korail_stations": _table_stats(references / "korail_stations.csv", {"station_id", "station_name", "normalized_station_name", "latitude", "longitude", "source"}),
        "subway_station_unmatched": _table_stats(references / "subway_station_unmatched.csv", {"line", "normalized_station_name"}),
    }
    optional = {
        "bus_stops": (references / "bus_stops.csv", {"city_code", "stop_id", "stop_name", "latitude", "longitude", "source", "coordinate_status"}),
        "bus_route_stops": (references / "bus_route_stops.csv", {"city_code", "route_id", "route_no", "route_name", "stop_id", "stop_name", "stop_sequence", "latitude", "longitude", "source", "coordinate_status"}),
        "bus_stop_unmatched": (references / "bus_stop_unmatched.csv", {"stop_id", "stop_name", "match_type"}),
        "bus_route_stop_unmatched": (references / "bus_route_stop_unmatched.csv", {"route_id", "stop_id", "stop_name"}),
        "seoul_bus_stops": (references / "seoul_bus_stops.csv", {"stop_id", "stop_name", "latitude", "longitude", "coordinate_source", "coordinate_status"}),
        "seoul_bus_route_stops": (references / "seoul_bus_route_stops.csv", {"route_id", "route_no", "route_name", "stop_id", "stop_name", "stop_sequence", "latitude", "longitude", "coordinate_source", "coordinate_status"}),
        "seoul_station_lines": (references / "seoul_station_lines.csv", {"station_id", "station_name", "normalized_station_name", "line", "external_code", "source"}),
        "subway_station_line_enrichment": (references / "subway_station_line_enrichment.csv", {"coordinate_station_id", "api_station_id", "line", "latitude", "longitude"}),
        "seoul_station_unmatched": (references / "seoul_station_unmatched.csv", {"line", "station_id", "station_name", "normalized_station_name"}),
    }
    for name, (path, required) in optional.items():
        if path.exists():
            tables[name] = _table_stats(path, required)
    credentials = load_transit_credentials()
    api_endpoints = json.loads(API_ENDPOINT_CONFIG.read_text(encoding="utf-8"))
    api_summary_path = references / "seoul_api_summary.json"
    api_summary = json.loads(api_summary_path.read_text(encoding="utf-8")) if api_summary_path.exists() else None
    tago_summary_path = references / "tago_api_summary.json"
    tago_summary = json.loads(tago_summary_path.read_text(encoding="utf-8")) if tago_summary_path.exists() else None
    bus_match_path = references / "bus_match_summary.json"
    bus_match_summary = json.loads(bus_match_path.read_text(encoding="utf-8")) if bus_match_path.exists() else None
    seoul_bus_match_path = references / "seoul_bus_match_summary.json"
    seoul_bus_summary = json.loads(seoul_bus_match_path.read_text(encoding="utf-8")) if seoul_bus_match_path.exists() else None
    live_validation = {
        "status": "NOT_CONNECTED",
        "report": "reports/transit_context/seoul_tago_live_validation.md",
        "cache": "data/cache/transit/tago_seoul_live_route_121900014.json",
    } if (PROJECT_ROOT / "reports/transit_context/seoul_tago_live_validation.md").exists() else None
    status = "INCOMPLETE_PENDING_FINAL_CHECKLIST"
    result = {
        "status": status,
        "completion_status": "INCOMPLETE",
        "api": {
            "configured_endpoints": api_endpoints,
            "data_go_kr_service_key": "configured" if credentials["data_go_kr_service_key"] else "API key unavailable",
            "seoul_openapi_key": "configured" if credentials["seoul_openapi_key"] else "API key unavailable",
            "live_calls_made": False,
            "seoul_api_summary": api_summary,
            "tago_api_summary": tago_summary,
            "bus_match_summary": bus_match_summary,
            "seoul_bus_match_summary": seoul_bus_summary,
            "seoul_tago_live_validation": live_validation,
            "note": "Seoul station-line and TAGO bus reference responses were called and cached; bus coordinates were joined from the supplied national file.",
        },
        "tables": tables,
        "bus_coordinate_match": bus_match_summary,
        "seoul_bus_reference": seoul_bus_summary,
        "seoul_tago_live_validation": live_validation,
        "unmatched_station_keys": tables["subway_station_unmatched"]["rows"],
        "limitations": [
            "TAGO references are currently limited to the requested 광주 서구 sample scope.",
            "TAGO BusStop and route-stop responses do not provide latitude/longitude; matched coordinates come only from the supplied national bus stop file.",
            "Seoul line API response was validated; coordinate coverage remains limited to the supplied 1-8 line file.",
            "GeoLife is not joined to Korean transit networks.",
            "Korail source has no line/subtype field; rail subtype remains unknown unless stronger evidence exists.",
        ],
    }
    (reports / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Transit Context validation",
        "",
        f"상태: `{result['status']}`",
        "",
        "## Reference 결과",
        "",
    ]
    for name, table in tables.items():
        lines.append(f"- {name}: {table['rows']:,} rows, duplicate {table['duplicate_rows']:,}, invalid coordinate {table['invalid_coordinate_rows']}")
    lines.append(f"- Seoul API response: {api_summary.get('status_code') if api_summary else 'not called'}")
    lines.append(f"- TAGO live/bus reference response: {tago_summary.get('status') if tago_summary else 'not called'}")
    if bus_match_summary:
        lines.extend([
            f"- BusStop API rows: {bus_match_summary.get('api_row_count', 0):,}",
            f"- National location file rows: {bus_match_summary.get('national_file_row_count', 0):,}",
            f"- Exact ID matches: {bus_match_summary.get('exact_id_match_count', 0):,}",
            f"- Name/region matches: {bus_match_summary.get('name_region_match_count', 0):,}",
            f"- Unmatched stops: {bus_match_summary.get('unmatched_count', 0):,}",
            f"- Stop coordinate match rate: {bus_match_summary.get('match_rate', 0.0):.3%}",
            f"- Route rows with coordinates: {bus_match_summary.get('route_coordinate_available_count', 0):,}",
            f"- Route rows without coordinates: {bus_match_summary.get('route_coordinate_missing_count', 0):,}",
        ])
    if seoul_bus_summary:
        lines.extend([
            f"- Seoul bus total stops: {seoul_bus_summary.get('stop_count', 0):,}",
            f"- Seoul bus coordinate stops: {seoul_bus_summary.get('coordinate_available_stop_count', 0):,}",
            f"- Seoul bus coordinate coverage: {seoul_bus_summary.get('coordinate_available_stop_count', 0) / seoul_bus_summary.get('stop_count', 1):.3%}",
            f"- Seoul bus routes: {seoul_bus_summary.get('route_count', 0):,}",
            f"- Seoul route-stop rows: {seoul_bus_summary.get('route_stop_rows', 0):,}",
            f"- Seoul route-stop coordinate coverage: {seoul_bus_summary.get('route_stop_coordinate_coverage', 0.0):.3%}",
            f"- Seoul invalid coordinate rows: {seoul_bus_summary.get('invalid_coordinate_rows', 0):,}",
            f"- Seoul duplicate route-stop rows removed: {seoul_bus_summary.get('duplicate_route_stop_rows_removed', 0):,}",
        ])
    if live_validation:
        lines.append(f"- Seoul TAGO live route join: {live_validation['status']} ({live_validation['report']})")
    lines.extend(["", "## API 상태", "", f"- DATA_GO_KR_SERVICE_KEY: {result['api']['data_go_kr_service_key']}", f"- SEOUL_OPENAPI_KEY: {result['api']['seoul_openapi_key']}", f"- Seoul API response: {api_summary.get('status_code') if api_summary else 'not called'}", f"- TAGO live/bus reference response: {tago_summary.get('status') if tago_summary else 'not called'}", "", "## 한계", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    (reports / "final_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", default="data/processed/transit_context")
    parser.add_argument("--report-dir", default="reports/transit_context")
    args = parser.parse_args()
    print(json.dumps(validate(args.reference_dir, args.report_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
