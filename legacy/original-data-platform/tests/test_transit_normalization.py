from pathlib import Path

import pandas as pd

from src.transit_context.normalization import (
    normalize_korail_stations,
    normalize_station_name,
    normalize_subway_stations,
    normalize_subway_timetable,
)


def test_station_name_normalization_is_exact_and_deterministic() -> None:
    assert normalize_station_name(" 서울 역 ") == "서울"
    assert normalize_station_name("역삼") == "역삼"


def test_normalize_supplied_transit_files() -> None:
    root = Path("data/raw/transit")
    stations = normalize_subway_stations(next(root.glob("*20250814.csv")))
    timetable = normalize_subway_timetable(next(root.glob("*20260616.csv")))
    korail = normalize_korail_stations(next(root.glob("*20240401.csv")))

    assert len(stations) == 276
    assert {"station_id", "line", "latitude", "longitude"} <= set(stations.columns)
    assert len(timetable) == 424264
    assert set(timetable["service_type"].dropna().unique()) == {"weekday", "saturday", "sunday_or_holiday"}
    assert len(korail) == 202
    assert korail["station_id"].str.startswith("korail:").all()


def test_coordinate_validation_drops_invalid_rows(tmp_path: Path) -> None:
    source = tmp_path / "stations.csv"
    pd.DataFrame(
        {
            "호선": ["1", "1"],
            "고유역번호(외부역코드)": ["1", "2"],
            "역명": ["정상역", "오류역"],
            "위도": [37.5, 120],
            "경도": [127.0, 127.0],
        }
    ).to_csv(source, index=False, encoding="cp949")
    result = normalize_subway_stations(source)
    assert result["station_name"].tolist() == ["정상역"]
