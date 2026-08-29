"""Seoul OpenAPI station-line adapter based on the observed response schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .api import TransitApiClient, require_key
from .normalization import normalize_station_name


SEOUL_STATION_LINE_ENDPOINT = "http://openapi.seoul.go.kr:8088/{key}/json/SearchSTNBySubwayLineInfo/1/{end}/"


def normalize_line(value: object) -> str:
    text = str(value).strip().lower()
    if text.endswith("호선"):
        text = text[:-2]
    if text.isdigit():
        return str(int(text))
    return text


def parse_seoul_station_line_payload(payload: dict[str, Any], *, source: str = "seoul_openapi") -> pd.DataFrame:
    root = payload.get("SearchSTNBySubwayLineInfo")
    if not isinstance(root, dict) or not isinstance(root.get("row"), list):
        raise ValueError("서울 역 노선 API 응답에 SearchSTNBySubwayLineInfo.row가 없습니다")
    rows = root["row"]
    required = {"STATION_CD", "STATION_NM", "LINE_NUM", "FR_CODE"}
    if rows and not required <= set(rows[0]):
        raise ValueError(f"서울 역 노선 API 응답 필드가 변경되었습니다: {sorted(required - set(rows[0]))}")
    result = pd.DataFrame(
        {
            "station_id": [str(row["STATION_CD"]).strip() for row in rows],
            "station_name": [str(row["STATION_NM"]).strip() for row in rows],
            "normalized_station_name": [normalize_station_name(row["STATION_NM"]) for row in rows],
            "line": [str(row["LINE_NUM"]).strip() for row in rows],
            "external_code": [str(row["FR_CODE"]).strip() for row in rows],
            "source": source,
        }
    )
    return result.drop_duplicates(["line", "station_id"], keep="first").reset_index(drop=True)


def merge_line_metadata(coordinates: pd.DataFrame, api_lines: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match API line metadata to supplied coordinates by normalized line and station name."""

    required_coordinates = {"station_id", "station_name", "normalized_station_name", "line", "latitude", "longitude"}
    required_api = {"station_id", "station_name", "normalized_station_name", "line", "external_code"}
    if not required_coordinates <= set(coordinates.columns) or not required_api <= set(api_lines.columns):
        raise ValueError("지하철 노선 metadata 결합에 필요한 컬럼이 없습니다")
    left = api_lines.copy()
    right = coordinates.copy()
    left["line_key"] = left["line"].map(normalize_line)
    right["line_key"] = right["line"].map(normalize_line)
    merged = left.merge(right, on=["line_key", "normalized_station_name"], how="left", suffixes=("_api", "_coordinate"), indicator=True)
    unmatched = merged.loc[merged["_merge"] == "left_only", ["line_api", "station_id_api", "station_name_api", "normalized_station_name"]].rename(columns={"line_api": "line", "station_id_api": "station_id", "station_name_api": "station_name"})
    matched = merged.loc[merged["_merge"] == "both", ["station_id_coordinate", "station_name_coordinate", "normalized_station_name", "line_coordinate", "latitude", "longitude", "station_id_api", "external_code", "source_api"]].rename(columns={"station_id_coordinate": "coordinate_station_id", "station_name_coordinate": "coordinate_station_name", "line_coordinate": "line", "station_id_api": "api_station_id", "source_api": "source"})
    return matched.reset_index(drop=True), unmatched.reset_index(drop=True)


def fetch_seoul_station_lines(api_key: str | None, *, cache_path: str | Path, refresh: bool = False, client: TransitApiClient | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    key = require_key(api_key, variable_name="SEOUL_OPENAPI_KEY")
    endpoint = SEOUL_STATION_LINE_ENDPOINT.format(key=key, end=1000)
    result = (client or TransitApiClient()).fetch_json(endpoint, params={}, cache_path=cache_path, refresh=refresh)
    frame = parse_seoul_station_line_payload(result.payload, source="seoul_openapi")
    root = result.payload["SearchSTNBySubwayLineInfo"]
    return frame, {"endpoint": "SearchSTNBySubwayLineInfo", "status_code": root.get("RESULT", {}).get("CODE"), "message": root.get("RESULT", {}).get("MESSAGE"), "list_total_count": root.get("list_total_count"), "row_count": len(frame), "from_cache": result.from_cache, "fields": sorted(root["row"][0]) if root.get("row") else []}
