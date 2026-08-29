"""Join TAGO bus stop records with the supplied national coordinate file.

TAGO's stop and route-stop responses identify stops but do not provide
coordinates.  This module only accepts exact identifier or exact
name-and-region matches; it never guesses a coordinate.
"""

from __future__ import annotations

import re
import unicodedata
import json
from pathlib import Path
from typing import Any

import pandas as pd


NATIONAL_COLUMNS = {
    "stop_id": "\uc815\ub958\uc7a5\ubc88\ud638",
    "stop_name": "\uc815\ub958\uc7a5\uba85",
    "latitude": "\uc704\ub3c4",
    "longitude": "\uacbd\ub3c4",
    "collection_date": "\uc815\ubcf4\uc218\uc9d1\uc77c",
    "mobile_short_no": "\ubaa8\ubc14\uc77c\ub2e8\ucd95\ubc88\ud638",
    "city_code": "\ub3c4\uc2dc\ucf54\ub4dc",
    "city_name": "\ub3c4\uc2dc\uba85",
    "managing_city_name": "\uad00\ub9ac\ub3c4\uc2dc\uba85",
}


def _normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)).strip().lower())


def read_national_bus_stops(path: str | Path) -> pd.DataFrame:
    """Read the official national bus stop file without changing the source."""

    source = Path(path)
    errors: list[str] = []
    raw: pd.DataFrame | None = None
    for encoding in ("cp949", "euc-kr", "utf-8-sig"):
        try:
            raw = pd.read_csv(source, encoding=encoding, dtype=str, low_memory=False)
            break
        except (UnicodeDecodeError, UnicodeError) as exc:
            errors.append(f"{encoding}: {exc}")
    if raw is None:
        raise UnicodeError(f"could not read national bus stop file {source}: {'; '.join(errors)}")
    missing = [column for column in NATIONAL_COLUMNS.values() if column not in raw.columns]
    if missing:
        raise ValueError(f"national bus stop file is missing columns: {missing}")
    result = pd.DataFrame({key: raw[column].astype("string").str.strip() for key, column in NATIONAL_COLUMNS.items()})
    result["normalized_stop_name"] = result["stop_name"].map(_normalize_text)
    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result["valid_coordinate"] = result["latitude"].between(-90, 90) & result["longitude"].between(-180, 180)
    return result


def _region_code_map(api_routes: pd.DataFrame, national: pd.DataFrame) -> dict[str, str]:
    """Map API region codes only when region names identify one file code."""

    code_column = "ctpv_cd" if "ctpv_cd" in api_routes else "city_code"
    if api_routes.empty or code_column not in api_routes or "ctpv_nm" not in api_routes:
        return {}
    national_names: dict[str, set[str]] = {}
    for code, name in zip(national["city_code"], national["city_name"]):
        key = _normalize_text(name)
        if key:
            national_names.setdefault(key, set()).add(str(code).strip())
    mapping: dict[str, str] = {}
    for code, name in api_routes[[code_column, "ctpv_nm"]].dropna().drop_duplicates().itertuples(index=False):
        candidates = national_names.get(_normalize_text(name), set())
        if len(candidates) == 1:
            mapping[str(code).strip()] = next(iter(candidates))
    return mapping


def match_bus_stops(api_stops: pd.DataFrame, national: pd.DataFrame, api_routes: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return coordinate-complete matches, unmatched rows, and auditable counts."""

    api = api_stops.copy().reset_index(drop=True)
    routes = api_routes if api_routes is not None else pd.DataFrame()
    region_map = _region_code_map(routes, national)
    national_by_id = national[national["stop_id"].ne("")].groupby("stop_id", dropna=False).size()
    national_name_code = national[national["valid_coordinate"]].groupby(["normalized_stop_name", "city_code"], dropna=False).size()
    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    exact_id_count = 0
    name_region_count = 0
    for _, row in api.iterrows():
        stop_id = str(row.get("stop_id", "")).strip()
        name = str(row.get("stop_name", "")).strip()
        candidate = national.iloc[0:0]
        match_type = "unmatched"
        if stop_id and national_by_id.get(stop_id, 0) == 1:
            candidate = national[national["stop_id"] == stop_id]
            if len(candidate) == 1 and bool(candidate.iloc[0]["valid_coordinate"]):
                match_type = "id_exact"
        if match_type == "unmatched":
            code = region_map.get(str(row.get("city_code", "")).strip())
            key = (_normalize_text(name), code)
            if key[0] and code and national_name_code.get(key, 0) == 1:
                candidate = national[(national["normalized_stop_name"] == key[0]) & (national["city_code"] == code)]
                if len(candidate) == 1:
                    match_type = "name_region_exact"
        if match_type != "unmatched":
            source = candidate.iloc[0]
            out = row.to_dict()
            out.update({"latitude": float(source["latitude"]), "longitude": float(source["longitude"]), "coordinate_source": "national_bus_stop_file", "national_stop_id": source["stop_id"], "national_stop_name": source["stop_name"], "national_city_code": source["city_code"], "match_type": match_type})
            matches.append(out)
            exact_id_count += match_type == "id_exact"
            name_region_count += match_type == "name_region_exact"
        else:
            unmatched.append({**row.to_dict(), "match_type": "unmatched", "region_code_used": region_map.get(str(row.get("city_code", "")).strip(), "")})
    matched = pd.DataFrame(matches)
    unmatched_frame = pd.DataFrame(unmatched)
    summary = {
        "api_row_count": int(len(api)),
        "exact_id_match_count": int(exact_id_count),
        "name_region_match_count": int(name_region_count),
        "matched_count": int(len(matched)),
        "unmatched_count": int(len(unmatched_frame)),
        "coordinate_available_count": int(len(matched)),
        "coordinate_missing_count": int(len(unmatched_frame)),
        "match_rate": float(len(matched) / len(api)) if len(api) else 0.0,
        "region_code_map": region_map,
        "matching_policy": "ID exact first; unique normalized name plus region second; ambiguous candidates remain unmatched",
    }
    return matched, unmatched_frame, summary


def join_route_stops(api_routes: pd.DataFrame, matched_stops: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach coordinates to route-stop rows using the resolved API stop ID."""

    coordinate_columns = ["stop_id", "latitude", "longitude", "coordinate_source", "match_type"]
    lookup = matched_stops[coordinate_columns].drop_duplicates("stop_id") if not matched_stops.empty else matched_stops.reindex(columns=coordinate_columns)
    joined = api_routes.merge(lookup, on="stop_id", how="left", suffixes=("", "_resolved"))
    valid = joined["latitude"].notna() & joined["longitude"].notna()
    return joined[valid].reset_index(drop=True), joined[~valid].reset_index(drop=True)


def build_bus_reference_files(api_stops: pd.DataFrame, api_routes: pd.DataFrame, national_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    national = read_national_bus_stops(national_path)
    matched, unmatched, summary = match_bus_stops(api_stops, national, api_routes)
    route_matched, route_unmatched = join_route_stops(api_routes, matched)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    matched.to_csv(output / "bus_stops.csv", index=False, encoding="utf-8-sig")
    route_matched.to_csv(output / "bus_route_stops.csv", index=False, encoding="utf-8-sig")
    unmatched.to_csv(output / "bus_stop_unmatched.csv", index=False, encoding="utf-8-sig")
    route_unmatched.to_csv(output / "bus_route_stop_unmatched.csv", index=False, encoding="utf-8-sig")
    summary.update({"national_file_row_count": int(len(national)), "route_api_row_count": int(len(api_routes)), "route_coordinate_available_count": int(len(route_matched)), "route_coordinate_missing_count": int(len(route_unmatched)), "route_match_rate": float(len(route_matched) / len(api_routes)) if len(api_routes) else 0.0})
    (output / "bus_match_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
