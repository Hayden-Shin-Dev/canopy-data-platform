import pytest

from src.transit_context.seoul_api import parse_seoul_station_line_payload


def test_parse_observed_seoul_station_line_response() -> None:
    frame = parse_seoul_station_line_payload({"SearchSTNBySubwayLineInfo": {"row": [{"STATION_CD": "1001", "STATION_NM": "서울역", "LINE_NUM": "01호선", "FR_CODE": "133"}]}})
    assert frame.loc[0, "station_id"] == "1001"
    assert frame.loc[0, "normalized_station_name"] == "서울"
    assert frame.loc[0, "line"] == "01호선"


def test_parse_seoul_api_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="SearchSTNBySubwayLineInfo"):
        parse_seoul_station_line_payload({"unexpected": {}})
