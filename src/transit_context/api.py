"""Safe HTTP and cache helpers for optional public transit APIs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import requests
from dotenv import load_dotenv

from src.config import PROJECT_ROOT


class ApiKeyUnavailable(RuntimeError):
    """Raised when an optional transit API key is not configured."""


@dataclass(frozen=True)
class ApiResult:
    payload: Any
    from_cache: bool
    endpoint: str


def load_transit_credentials(*, env_path: str | Path | None = None) -> dict[str, str | None]:
    """Load transit keys from the project .env without printing or committing them."""

    path = Path(env_path) if env_path else PROJECT_ROOT / ".env"
    load_dotenv(path, override=False)
    import os

    return {
        "data_go_kr_service_key": os.getenv("DATA_GO_KR_SERVICE_KEY"),
        "seoul_openapi_key": os.getenv("SEOUL_OPENAPI_KEY"),
    }


class TransitApiClient:
    def __init__(self, *, session: requests.Session | None = None, timeout_seconds: float = 15, retries: int = 3, pause_seconds: float = 0.2):
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.pause_seconds = pause_seconds

    def fetch_json(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any],
        cache_path: str | Path | None = None,
        refresh: bool = False,
    ) -> ApiResult:
        cache = Path(cache_path) if cache_path else None
        if cache and cache.exists() and not refresh:
            return ApiResult(json.loads(cache.read_text(encoding="utf-8")), True, endpoint)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(endpoint, params=dict(params), timeout=self.timeout_seconds)
                if response.status_code in {401, 403, 429}:
                    raise requests.HTTPError(f"transit API authorization/rate-limit status={response.status_code}", response=response)
                response.raise_for_status()
                payload = response.json()
                if cache:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                return ApiResult(payload, False, endpoint)
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.pause_seconds * (attempt + 1))
        assert last_error is not None
        raise last_error


def require_key(value: str | None, *, variable_name: str) -> str:
    if not value or not value.strip():
        raise ApiKeyUnavailable(f"{variable_name}가 설정되지 않아 API 호출을 건너뜁니다")
    return value.strip()
