"""Normalize Seoul's official bus route-stop file.

The Seoul source carries route, ordered stop, NODE_ID and X/Y in one record.
Using NODE_ID inside that source avoids a name-based join for the Seoul POC.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_COLUMNS = {
    "route_id": "ROUTE_ID",
    "route_name": "\ub178\uc120\uba85",
    "stop_sequence": "\uc21c\ubc88",
    "stop_id": "NODE_ID",
    "ars_id": "ARS_ID",
    "stop_name": "\uc815\ub958\uc18c\uba85",
    "longitude": "X\uc88c\ud45c",
    "latitude": "Y\uc88c\ud45c",
}
SOURCE_CATALOG_URL = "https://data.seoul.go.kr/dataList/OA-1095/S/1/datasetView.do"


def read_seoul_bus_route_stops(path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read and validate the official Seoul route-stop workbook."""

    source = Path(path)
    raw = pd.read_excel(source, dtype=str)
    missing = [column for column in SOURCE_COLUMNS.values() if column not in raw.columns]
    if missing:
        raise ValueError(f"Seoul bus source is missing columns: {missing}")
    result = pd.DataFrame(
        {
            "route_id": raw[SOURCE_COLUMNS["route_id"]].astype("string").str.strip(),
            # The source exposes one route-name field; retain it in both required views.
            "route_no": raw[SOURCE_COLUMNS["route_name"]].astype("string").str.strip(),
            "route_name": raw[SOURCE_COLUMNS["route_name"]].astype("string").str.strip(),
            "stop_sequence": pd.to_numeric(raw[SOURCE_COLUMNS["stop_sequence"]], errors="coerce"),
            "stop_id": raw[SOURCE_COLUMNS["stop_id"]].astype("string").str.strip(),
            "stop_name": raw[SOURCE_COLUMNS["stop_name"]].astype("string").str.strip(),
            "ars_id": raw[SOURCE_COLUMNS["ars_id"]].astype("string").str.strip(),
            "longitude": pd.to_numeric(raw[SOURCE_COLUMNS["longitude"]], errors="coerce"),
            "latitude": pd.to_numeric(raw[SOURCE_COLUMNS["latitude"]], errors="coerce"),
            "source": source.name,
            "coordinate_source": "seoul_official_route_stop_file",
            "coordinate_status": "provided_by_source",
        }
    )
    valid = (
        result["route_id"].ne("")
        & result["stop_id"].ne("")
        & result["stop_sequence"].notna()
        & result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    )
    clean = result[valid].drop_duplicates(["route_id", "stop_sequence"], keep="first").reset_index(drop=True)
    stop_groups = clean.groupby("stop_id", dropna=False)
    stops = stop_groups.agg(
        stop_name=("stop_name", "first"),
        ars_id=("ars_id", "first"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        source=("source", "first"),
        coordinate_source=("coordinate_source", "first"),
        coordinate_status=("coordinate_status", "first"),
    ).reset_index()
    summary = {
        "source_file": str(source),
        "source_catalog_url": SOURCE_CATALOG_URL,
        "raw_route_stop_rows": int(len(raw)),
        "route_stop_rows": int(len(clean)),
        "route_count": int(clean["route_id"].nunique()),
        "stop_count": int(len(stops)),
        "coordinate_available_stop_count": int(stops[["latitude", "longitude"]].notna().all(axis=1).sum()),
        "invalid_coordinate_rows": int((~valid).sum()),
        "duplicate_route_stop_rows_removed": int(len(result) - len(clean)),
        "duplicate_stop_id_count": int(clean["stop_id"].duplicated().sum()),
        "route_stop_coordinate_coverage": float(len(clean) and clean[["latitude", "longitude"]].notna().all(axis=1).mean()),
        "join_key": "NODE_ID",
        "coordinate_system": "observed longitude/latitude values; WGS84 geographic coordinates",
    }
    return stops, clean, summary


def build_seoul_bus_reference(path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    stops, route_stops, summary = read_seoul_bus_route_stops(path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stops.to_csv(output / "seoul_bus_stops.csv", index=False, encoding="utf-8-sig")
    route_stops.to_csv(output / "seoul_bus_route_stops.csv", index=False, encoding="utf-8-sig")
    import json

    (output / "seoul_bus_match_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
