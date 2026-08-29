"""TAGO API bootstrap calls with explicit error reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from urllib.parse import unquote

from .api import TransitApiClient, require_key


TAGO_CITY_CODES_ENDPOINT = "http://apis.data.go.kr/1613000/BusLcInfoInqireService/getCtyCodeList"
TAGO_SERVICE_ENDPOINTS = {
    "bus_stops": "http://apis.data.go.kr/1613000/BusSttnInfoInqireService/getCtyCodeList",
    "bus_routes": "http://apis.data.go.kr/1613000/BusRouteInfoInqireService/getCtyCodeList",
    "bus_locations": TAGO_CITY_CODES_ENDPOINT,
}


def fetch_tago_city_codes(api_key: str | None, *, cache_path: str | Path, refresh: bool = False, client: TransitApiClient | None = None) -> tuple[Any | None, dict[str, object]]:
    key = unquote(require_key(api_key, variable_name="DATA_GO_KR_SERVICE_KEY"))
    try:
        result = (client or TransitApiClient()).fetch_json(TAGO_CITY_CODES_ENDPOINT, params={"ServiceKey": key, "_type": "json", "numOfRows": 100, "pageNo": 1}, cache_path=cache_path, refresh=refresh)
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
            result = active_client.fetch_json(endpoint, params={"ServiceKey": key, "_type": "json", "numOfRows": 1, "pageNo": 1}, refresh=True)
            results[name] = {"endpoint": endpoint, "status": "success", "from_cache": result.from_cache}
        except requests.HTTPError as exc:
            response = exc.response
            results[name] = {"endpoint": endpoint, "status": "http_error", "status_code": response.status_code if response is not None else None, "response_body": response.text[:1000] if response is not None else str(exc)}
        except requests.RequestException as exc:
            results[name] = {"endpoint": endpoint, "status": "request_error", "error_type": type(exc).__name__, "error": str(exc)}
    return results
