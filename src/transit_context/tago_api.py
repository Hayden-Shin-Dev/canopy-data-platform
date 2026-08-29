"""TAGO API bootstrap calls with explicit error reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from urllib.parse import unquote

from .api import TransitApiClient, require_key


TAGO_CITY_CODES_ENDPOINT = "https://apis.data.go.kr/1613000/BusLcInfoInqireService/getCtyCodeList"
TAGO_SERVICE_ENDPOINTS = {
    "bus_stops": "https://apis.data.go.kr/1613000/BusStop/getBusStop",
    "bus_routes": "https://apis.data.go.kr/1613000/BusRoutespecificStopInformation/getBusRoutespecificStopInformation",
    "bus_locations": TAGO_CITY_CODES_ENDPOINT,
}

TAGO_SAMPLE_SCOPE = {"opr_ymd": "20250801", "ctpv_cd": "29", "sgg_cd": "29140"}


def fetch_tago_city_codes(api_key: str | None, *, cache_path: str | Path, refresh: bool = False, client: TransitApiClient | None = None) -> tuple[Any | None, dict[str, object]]:
    key = unquote(require_key(api_key, variable_name="DATA_GO_KR_SERVICE_KEY"))
    try:
        result = (client or TransitApiClient()).fetch_json(TAGO_CITY_CODES_ENDPOINT, params={"serviceKey": key, "_type": "json", "numOfRows": 100, "pageNo": 1}, cache_path=cache_path, refresh=refresh)
        payload = result.payload
        return payload, {"endpoint": TAGO_CITY_CODES_ENDPOINT, "status": "success", "from_cache": result.from_cache}
    except requests.HTTPError as exc:
        response = exc.response
        body = response.text[:1000] if response is not None else str(exc)
        return None, {"endpoint": TAGO_CITY_CODES_ENDPOINT, "status": "http_error", "status_code": response.status_code if response is not None else None, "response_body": body}
    except requests.RequestException as exc:
        return None, {"endpoint": TAGO_CITY_CODES_ENDPOINT, "status": "request_error", "error_type": type(exc).__name__, "error": str(exc)}


def probe_tago_services(api_key: str | None, *, client: TransitApiClient | None = None) -> dict[str, object]:
    """Probe each separately subscribed TAGO service without inventing data."""

    key = unquote(require_key(api_key, variable_name="DATA_GO_KR_SERVICE_KEY"))
    active_client = client or TransitApiClient()
    results: dict[str, object] = {}
    for name, endpoint in TAGO_SERVICE_ENDPOINTS.items():
        try:
            params = {"serviceKey": key, "dataType": "JSON", "_type": "json", "numOfRows": 1, "pageNo": 1}
            if name == "bus_stops":
                params.update({"opr_ymd": "20250801", "ctpv_cd": "29", "sgg_cd": "29140"})
            elif name == "bus_routes":
                params.update({"opr_ymd": "20250801", "ctpv_cd": "29", "sgg_cd": "29140"})
            result = active_client.fetch_json(endpoint, params=params, refresh=True)
            results[name] = {"endpoint": endpoint, "status": "success", "from_cache": result.from_cache}
        except requests.HTTPError as exc:
            response = exc.response
            results[name] = {"endpoint": endpoint, "status": "http_error", "status_code": response.status_code if response is not None else None, "response_body": response.text[:1000] if response is not None else str(exc)}
        except requests.RequestException as exc:
            results[name] = {"endpoint": endpoint, "status": "request_error", "error_type": type(exc).__name__, "error": str(exc)}
    return results


def _payload_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    root = payload.get("response") or payload.get("Response")
    if not isinstance(root, dict):
        raise ValueError("TAGO 응답에 response/Response 객체가 없습니다")
    body = root.get("body")
    if not isinstance(body, dict):
        raise ValueError("TAGO 응답에 body 객체가 없습니다")
    items = body.get("items")
    if isinstance(items, dict) and isinstance(items.get("item"), list):
        return items["item"]
    if items in (None, ""):
        return []
    if isinstance(items, list):
        return items
    raise ValueError("TAGO 응답의 items 형식이 변경되었습니다")


def parse_tago_bus_stops(payload: dict[str, Any], *, source: str = "tago_bus_stop") -> Any:
    import pandas as pd
    rows = _payload_rows(payload)
    result = pd.DataFrame(rows)
    required = {"sttn_id", "sttn_nm", "ctpv_cd"}
    if not required <= set(result.columns):
        raise ValueError(f"TAGO BusStop 응답 필드가 없습니다: {sorted(required - set(result.columns))}")
    result = result.rename(columns={"ctpv_cd": "city_code", "sttn_id": "stop_id", "sttn_nm": "stop_name"})
    result["latitude"], result["longitude"] = pd.NA, pd.NA
    result["source"] = source
    result["coordinate_status"] = "not_provided_by_api"
    return result


def parse_tago_route_stops(payload: dict[str, Any], *, source: str = "tago_route_specific_stop") -> Any:
    import pandas as pd
    rows = _payload_rows(payload)
    result = pd.DataFrame(rows)
    required = {"rte_id", "rte_no", "rte_nm", "sttn_seq", "sttn_id", "sttn_nm", "ctpv_cd"}
    if not required <= set(result.columns):
        raise ValueError(f"TAGO route-stop 응답 필드가 없습니다: {sorted(required - set(result.columns))}")
    result = result.rename(columns={"ctpv_cd": "city_code", "rte_id": "route_id", "rte_no": "route_no", "rte_nm": "route_name", "sttn_seq": "stop_sequence", "sttn_id": "stop_id", "sttn_nm": "stop_name"})
    result["latitude"], result["longitude"] = pd.NA, pd.NA
    result["source"] = source
    result["coordinate_status"] = "not_provided_by_api"
    return result
