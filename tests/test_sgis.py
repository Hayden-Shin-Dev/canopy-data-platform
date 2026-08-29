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
    parse_boundary_response,
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


def test_client_refreshes_token_on_http_401() -> None:
    session = Mock()
    session.get.side_effect = [
        _response({"errCd": 0, "result": {"accessToken": "old"}}),
        _response({}, status_code=401),
        _response({"errCd": 0, "result": {"accessToken": "new"}}),
        _response({"errCd": 0, "features": []}),
    ]
    client = SgisClient("key", "secret", session=session, request_interval_seconds=0)

    assert client.request_boundary()["features"] == []


def test_parse_boundary_response_reads_representative_coordinates() -> None:
    records = parse_boundary_response(
        {
            "errCd": 0,
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [[[1, 2], [3, 4]]]},
                    "properties": {
                        "adm_cd": "1101053",
                        "adm_nm": "서울특별시 종로구 사직동",
                        "x": "953808.5",
                        "y": "1952441.25",
                    },
                }
            ],
        }
    )

    assert records[0].adm_cd == "1101053"
    assert records[0].adm_nm == "서울특별시 종로구 사직동"
    assert records[0].x == pytest.approx(953808.5)
    assert records[0].y == pytest.approx(1952441.25)


def test_parse_boundary_response_does_not_average_polygon_when_xy_is_missing() -> None:
    records = parse_boundary_response(
        {
            "errCd": 0,
            "features": [
                {
                    "geometry": {"type": "Polygon", "coordinates": [[[1, 2], [3, 4]]]},
                    "properties": {"adm_cd": "1101053", "adm_nm": "서울특별시 종로구 사직동"},
                }
            ],
        }
    )

    assert records[0].x is None
    assert records[0].y is None
