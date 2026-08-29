from pathlib import Path

import requests

from src.transit_context.tago_api import fetch_tago_city_codes


class ErrorSession:
    def get(self, endpoint, *, params, timeout):
        response = requests.Response()
        response.status_code = 403
        response._content = b'{"error":"SERVICE_KEY_IS_NOT_REGISTERED_ERROR"}'
        response.url = endpoint
        raise requests.HTTPError("forbidden", response=response)


class ErrorClient:
    def fetch_json(self, *args, **kwargs):
        ErrorSession().get("x", params={}, timeout=1)


def test_tago_error_is_reported_without_raising(tmp_path: Path) -> None:
    payload, summary = fetch_tago_city_codes("key", cache_path=tmp_path / "tago.json", client=ErrorClient())
    assert payload is None
    assert summary["status"] == "http_error"
    assert summary["status_code"] == 403
