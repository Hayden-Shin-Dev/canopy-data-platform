from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
import requests

from src.ktdb.sgis import (
    AUTH_URL,
    BOUNDARY_URL,
    SgisClient,
    SgisApiError,
    load_sgis_credentials,
    parse_authentication_response,
)


def _response(payload: dict[str, object], status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


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


def test_client_retries_timeout_before_authentication_success() -> None:
    session = Mock()
    session.get.side_effect = [
        requests.Timeout("slow"),
        _response({"errCd": 0, "result": {"accessToken": "token"}}),
    ]
    sleep = Mock()
    client = SgisClient("key", "secret", session=session, max_retries=1, sleep=sleep)

    assert client.authenticate().access_token == "token"
    assert session.get.call_count == 2
    assert session.get.call_args_list[0].args[0] == AUTH_URL
    sleep.assert_called_once_with(1)


def test_client_refreshes_expired_token_and_repeats_boundary_request() -> None:
    session = Mock()
    session.get.side_effect = [
        _response({"errCd": 0, "result": {"accessToken": "old"}}),
        _response({"errCd": -401, "errMsg": "expired"}),
        _response({"errCd": 0, "result": {"accessToken": "new"}}),
        _response({"errCd": 0, "features": []}),
    ]
    client = SgisClient("key", "secret", session=session, request_interval_seconds=0)

    assert client.request_boundary(adm_cd="11")["features"] == []
    assert [call.args[0] for call in session.get.call_args_list] == [
        AUTH_URL,
        BOUNDARY_URL,
        AUTH_URL,
        BOUNDARY_URL,
    ]
    final_params = session.get.call_args_list[-1].kwargs["params"]
    assert final_params["accessToken"] == "new"
    assert final_params["adm_cd"] == "11"
