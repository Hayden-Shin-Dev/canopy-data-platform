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
    credentials = load_transit_credentials()
    api_endpoints = json.loads(API_ENDPOINT_CONFIG.read_text(encoding="utf-8"))
    result = {
        "status": "reference_only_api_pending",
        "api": {
            "configured_endpoints": api_endpoints,
            "data_go_kr_service_key": "configured" if credentials["data_go_kr_service_key"] else "API key unavailable",
            "seoul_openapi_key": "configured" if credentials["seoul_openapi_key"] else "API key unavailable",
            "live_calls_made": False,
            "note": "No API response is reported until keys are configured and endpoints are called.",
        },
        "tables": tables,
        "unmatched_station_keys": tables["subway_station_unmatched"]["rows"],
        "limitations": [
            "Bus references and live positions were not fetched without DATA_GO_KR_SERVICE_KEY.",
            "Seoul line API enrichment was not fetched without SEOUL_OPENAPI_KEY.",
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
    lines.extend(["", "## API 상태", "", f"- DATA_GO_KR_SERVICE_KEY: {result['api']['data_go_kr_service_key']}", f"- SEOUL_OPENAPI_KEY: {result['api']['seoul_openapi_key']}", "- 실제 API 호출: 없음", "", "## 한계", ""])
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
