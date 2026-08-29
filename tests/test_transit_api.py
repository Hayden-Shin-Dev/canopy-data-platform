import json
from pathlib import Path

import pytest
import requests

from src.transit_context.api import ApiKeyUnavailable, TransitApiClient, require_key


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"items": [{"id": "1"}]}


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get(self, endpoint, *, params, timeout):
        self.calls += 1
        return FakeResponse()


def test_api_result_is_cached(tmp_path: Path) -> None:
    cache = tmp_path / "response.json"
    session = FakeSession()
    client = TransitApiClient(session=session)
    first = client.fetch_json("https://example.test", params={"page": 1}, cache_path=cache)
    second = client.fetch_json("https://example.test", params={"page": 1}, cache_path=cache)
    assert first.from_cache is False
    assert second.from_cache is True
    assert session.calls == 1
    assert json.loads(cache.read_text()) == {"items": [{"id": "1"}]}


def test_require_key_reports_missing_without_revealing_value() -> None:
    with pytest.raises(ApiKeyUnavailable, match="DATA_GO_KR_SERVICE_KEY"):
        require_key("", variable_name="DATA_GO_KR_SERVICE_KEY")
