"""조사일과 출발 시각에서 모델용 시간 Feature를 만든다."""

from __future__ import annotations

import pandas as pd

from src.config import MINUTE_BIN_SIZE, TIME_BANDS


def parse_survey_date(values: pd.Series, year: int = 2021) -> pd.Series:
    """Code Book의 DATE(MMDD)를 해당 연도의 날짜로 변환한다."""

    text = values.astype("string").str.strip()
    text = text.where(text.eq(""), text.str.zfill(4))
    dates = pd.to_datetime(
        text.mask(text.eq(""), pd.NA).map(lambda value: f"{year}{value}"),
        format="%Y%m%d",
        errors="coerce",
    )
    return dates


def _normalise_hour(values: pd.Series) -> pd.Series:
    hours = pd.to_numeric(values, errors="coerce")
    valid = hours.between(0, 27)
    return hours.where(valid).mod(24).astype("Int64")


def _time_band(hour: object) -> str | pd.NA:
    if pd.isna(hour):
        return pd.NA
    hour_int = int(hour)
    for name, start, end in TIME_BANDS:
        if start <= hour_int < end:
            return name
    return pd.NA


def derive_time_features(frame: pd.DataFrame, year: int = 2021) -> pd.DataFrame:
    """DATE·TP3_1·TP3_2를 검증 가능한 시간 Feature로 확장한다."""

    required = {"DATE", "TP3_1", "TP3_2"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"시간 Feature에 필요한 컬럼이 없음: {sorted(missing)}")

    result = frame.copy()
    survey_dates = parse_survey_date(result["DATE"], year=year)
    result["survey_date"] = survey_dates.dt.strftime("%Y-%m-%d").astype("string")
    result["weekday"] = survey_dates.dt.strftime("%a").astype("string")
    result["departure_hour"] = _normalise_hour(result["TP3_1"])

    minutes = pd.to_numeric(result["TP3_2"], errors="coerce")
    valid_minutes = minutes.between(0, 59)
    result["departure_minute_bin"] = (
        (minutes.where(valid_minutes) // MINUTE_BIN_SIZE) * MINUTE_BIN_SIZE
    ).astype("Int64")
    result["time_band"] = result["departure_hour"].map(_time_band).astype("string")
    return result
