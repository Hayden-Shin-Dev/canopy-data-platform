"""SGIS OpenAPI 인증과 행정구역 reference 수집 지원."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests


AUTH_URL = "https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json"
BOUNDARY_URL = "https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson"
SGIS_YEAR = "2021"
TOKEN_EXPIRED_CODE = -401


class SgisApiError(RuntimeError):
    """SGIS가 오류 응답을 반환했거나 응답 계약을 지키지 않은 경우."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SgisToken:
    access_token: str
    expires_at: int | None


@dataclass(frozen=True)
class SgisBoundaryRecord:
    adm_cd: str
    adm_nm: str
    x: float | None
    y: float | None


def _error_code(payload: Mapping[str, Any]) -> int | None:
    value = payload.get("errCd")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise SgisApiError("SGIS errCd 형식이 올바르지 않습니다") from error


def ensure_sgis_success(payload: Mapping[str, Any]) -> None:
    """공통 errCd 값을 확인하고 실패 응답을 예외로 바꾼다."""

    code = _error_code(payload)
    if code in (None, 0):
        return
    message = str(payload.get("errMsg") or "SGIS API 요청에 실패했습니다")
    raise SgisApiError(message, code=code)


def parse_authentication_response(payload: Mapping[str, Any]) -> SgisToken:
    """인증 응답에서 access token과 만료 시각을 읽는다."""

    ensure_sgis_success(payload)
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise SgisApiError("SGIS 인증 응답에 result가 없습니다")
    access_token = str(result.get("accessToken") or "").strip()
    if not access_token:
        raise SgisApiError("SGIS 인증 응답에 accessToken이 없습니다")
    timeout = result.get("accessTimeout")
    try:
        expires_at = int(timeout) if timeout not in (None, "") else None
    except (TypeError, ValueError) as error:
        raise SgisApiError("SGIS accessTimeout 형식이 올바르지 않습니다") from error
    return SgisToken(access_token=access_token, expires_at=expires_at)


def _optional_coordinate(value: object, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise SgisApiError(f"SGIS {field_name} 좌표 형식이 올바르지 않습니다") from error


def parse_boundary_response(payload: Mapping[str, Any]) -> list[SgisBoundaryRecord]:
    """GeoJSON properties만 읽고 polygon으로 대표점을 만들지 않는다."""

    ensure_sgis_success(payload)
    features = payload.get("features")
    if not isinstance(features, list):
        raise SgisApiError("SGIS 경계 응답에 features 목록이 없습니다")
    records: list[SgisBoundaryRecord] = []
    for feature in features:
        if not isinstance(feature, Mapping):
            raise SgisApiError("SGIS 경계 feature 형식이 올바르지 않습니다")
        properties = feature.get("properties")
        if not isinstance(properties, Mapping):
            raise SgisApiError("SGIS 경계 feature에 properties가 없습니다")
        adm_cd = str(properties.get("adm_cd") or "").strip()
        adm_nm = str(properties.get("adm_nm") or "").strip()
        if not adm_cd or not adm_nm:
            raise SgisApiError("SGIS 경계 properties에 adm_cd 또는 adm_nm이 없습니다")
        records.append(
            SgisBoundaryRecord(
                adm_cd=adm_cd,
                adm_nm=adm_nm,
                x=_optional_coordinate(properties.get("x"), "x"),
                y=_optional_coordinate(properties.get("y"), "y"),
            )
        )
    return records


def load_sgis_credentials() -> tuple[str, str]:
    """키를 파일이나 코드가 아닌 현재 프로세스 환경에서만 읽는다."""

    consumer_key = os.environ.get("SGIS_CONSUMER_KEY", "").strip()
    consumer_secret = os.environ.get("SGIS_CONSUMER_SECRET", "").strip()
    missing = [
        name
        for name, value in (
            ("SGIS_CONSUMER_KEY", consumer_key),
            ("SGIS_CONSUMER_SECRET", consumer_secret),
        )
        if not value
    ]
    if missing:
        raise SgisApiError(f"SGIS 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
    return consumer_key, consumer_secret


class SgisClient:
    """timeout, 재시도, 토큰 갱신을 한곳에서 처리하는 SGIS HTTP client."""

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        *,
        session: requests.Session | None = None,
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        request_interval_seconds: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not consumer_key or not consumer_secret:
            raise ValueError("SGIS consumer key와 secret이 필요합니다")
        if timeout_seconds <= 0 or max_retries < 0 or request_interval_seconds < 0:
            raise ValueError("SGIS 요청 설정값은 음수가 될 수 없습니다")
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._session = session or requests.Session()
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._request_interval_seconds = request_interval_seconds
        self._sleep = sleep
        self._token: SgisToken | None = None
        self._last_boundary_request_at: float | None = None

    def _get_json(self, url: str, params: Mapping[str, object]) -> Mapping[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self._timeout_seconds)
                if response.status_code == 401:
                    raise SgisApiError("SGIS HTTP 인증 토큰이 만료되었습니다", code=TOKEN_EXPIRED_CODE)
                if response.status_code >= 500:
                    raise requests.HTTPError(f"SGIS HTTP {response.status_code}", response=response)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, Mapping):
                    raise SgisApiError("SGIS 응답이 JSON object가 아닙니다")
                return payload
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                self._sleep(min(2**attempt, 4))
            except ValueError as error:
                raise SgisApiError("SGIS 응답을 JSON으로 해석할 수 없습니다") from error
        raise SgisApiError(f"SGIS 요청 재시도 한도를 초과했습니다: {last_error}") from last_error

    def authenticate(self, *, force: bool = False) -> SgisToken:
        if self._token is not None and not force:
            return self._token
        payload = self._get_json(
            AUTH_URL,
            {
                "consumer_key": self._consumer_key,
                "consumer_secret": self._consumer_secret,
            },
        )
        self._token = parse_authentication_response(payload)
        return self._token

    def _wait_for_boundary_interval(self) -> None:
        now = time.monotonic()
        if self._last_boundary_request_at is not None:
            remaining = self._request_interval_seconds - (now - self._last_boundary_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_boundary_request_at = time.monotonic()

    def request_boundary(
        self,
        *,
        adm_cd: str | None = None,
        low_search: int = 1,
        year: str = SGIS_YEAR,
    ) -> Mapping[str, Any]:
        if low_search not in {0, 1, 2}:
            raise ValueError("low_search는 0, 1, 2 중 하나여야 합니다")
        token = self.authenticate()
        params: dict[str, object] = {
            "accessToken": token.access_token,
            "year": year,
            "low_search": low_search,
        }
        if adm_cd:
            params["adm_cd"] = adm_cd

        for refresh_attempt in range(2):
            self._wait_for_boundary_interval()
            payload = self._get_json(BOUNDARY_URL, params)
            try:
                ensure_sgis_success(payload)
                return payload
            except SgisApiError as error:
                if error.code != TOKEN_EXPIRED_CODE or refresh_attempt == 1:
                    raise
                token = self.authenticate(force=True)
                params["accessToken"] = token.access_token
        raise AssertionError("SGIS token refresh loop reached an invalid state")
