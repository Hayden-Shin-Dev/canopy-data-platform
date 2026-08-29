from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.ktdb.sgis import (
    SgisApiError,
    load_sgis_credentials,
    parse_authentication_response,
)


def test_parse_authentication_response_reads_token_and_timeout() -> None:
    token = parse_authentication_response(
        {
            "errCd": 0,
            "errMsg": "Success",
            "result": {"accessToken": "test-token", "accessTimeout": "1787990400"},
        }
    )

    assert token.access_token == "test-token"
    assert token.expires_at == 1787990400


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"errCd": -401, "errMsg": "Token expired"}, "Token expired"),
        ({"errCd": 0, "result": {}}, "accessToken"),
        ({"errCd": 0, "result": {"accessToken": "token", "accessTimeout": "bad"}}, "accessTimeout"),
    ],
)
def test_parse_authentication_response_rejects_invalid_payloads(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(SgisApiError, match=message):
        parse_authentication_response(payload)


def test_load_sgis_credentials_reads_environment_only() -> None:
    with patch.dict(
        os.environ,
        {"SGIS_CONSUMER_KEY": "key", "SGIS_CONSUMER_SECRET": "secret"},
        clear=True,
    ):
        assert load_sgis_credentials() == ("key", "secret")


def test_load_sgis_credentials_reports_missing_names() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SgisApiError, match="SGIS_CONSUMER_KEY.*SGIS_CONSUMER_SECRET"):
            load_sgis_credentials()
