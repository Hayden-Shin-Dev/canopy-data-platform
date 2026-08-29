"""SGIS OpenAPI 인증과 행정구역 reference 수집 지원."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


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
