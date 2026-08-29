"""TAGO API bootstrap calls with explicit error reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from .api import TransitApiClient, require_key


TAGO_CITY_CODES_ENDPOINT = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService/getCtyCodeList"


def fetch_tago_city_codes(api_key: str | None, *, cache_path: str | Path, refresh: bool = False, client: TransitApiClient | None = None) -> tuple[Any | None, dict[str, object]]:
    key = require_key(api_key, variable_name="DATA_GO_KR_SERVICE_KEY")
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
