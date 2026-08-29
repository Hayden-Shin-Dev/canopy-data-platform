import json
from pathlib import Path

from scripts.validate_transit_context import validate


def test_validate_reference_tables_writes_report(tmp_path: Path) -> None:
    reference = tmp_path / "references"
    reference.mkdir()
    (reference / "subway_stations.csv").write_text("station_id,station_name,normalized_station_name,line,latitude,longitude,source\n1,A,a,1,37.5,127.0,test\n", encoding="utf-8-sig")
    (reference / "subway_timetable.csv").write_text("line,station_id,station_name,normalized_station_name,direction,service_type,service_type_raw,arrival_time,departure_time,source\n1,1,A,a,UP,weekday,DAY,05:00,05:01,test\n", encoding="utf-8-sig")
    (reference / "korail_stations.csv").write_text("station_id,station_name,normalized_station_name,latitude,longitude,source,region\nkorail:a,A,a,37.5,127.0,test,R\n", encoding="utf-8-sig")
    (reference / "subway_station_unmatched.csv").write_text("line,normalized_station_name\n", encoding="utf-8-sig")
    result = validate(reference, tmp_path / "reports")
    assert result["tables"]["subway_stations"]["rows"] == 1
    assert json.loads((tmp_path / "reports" / "validation.json").read_text())["status"] == "reference_only_api_pending"
