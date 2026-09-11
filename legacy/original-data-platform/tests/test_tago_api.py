from pathlib import Path

import requests

from src.transit_context.tago_api import fetch_tago_city_codes, parse_tago_bus_stops, parse_tago_route_stops, probe_tago_services


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


class SuccessClient:
    def fetch_json(self, *args, **kwargs):
        return type("Result", (), {"from_cache": False, "payload": {}})()


def test_tago_service_probe_keeps_service_statuses_separate() -> None:
    result = probe_tago_services("key", client=SuccessClient())
    assert set(result) == {"bus_stops", "bus_routes", "bus_locations"}
    assert all(item["status"] == "success" for item in result.values())


def test_parse_observed_bus_stop_schema_does_not_invent_coordinates() -> None:
    frame = parse_tago_bus_stops({"Response": {"body": {"items": {"item": [{"sttn_id": "s1", "sttn_nm": "정류장", "ctpv_cd": "29"}]}}}})
    assert frame.loc[0, "stop_id"] == "s1"
    assert frame.loc[0, "coordinate_status"] == "not_provided_by_api"


def test_parse_observed_route_stop_schema() -> None:
    frame = parse_tago_route_stops({"response": {"body": {"items": {"item": [{"rte_id": "r1", "rte_no": "1", "rte_nm": "1번", "sttn_seq": 1, "sttn_id": "s1", "sttn_nm": "정류장", "ctpv_cd": "29"}]}}}})
    assert frame.loc[0, "route_id"] == "r1"
    assert frame.loc[0, "stop_sequence"] == 1
