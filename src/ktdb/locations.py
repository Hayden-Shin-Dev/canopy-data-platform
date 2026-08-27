"""출발·도착 행정구역과 OD 범위를 파생한다."""

from __future__ import annotations

import pandas as pd


LOCATION_COLUMNS = {
    "sTP1_1_5": "origin_admin_dong",
    "sTP1_1_6": "origin_sido",
    "sTP1_1_7": "origin_sigungu",
    "TP1_1_5": "destination_admin_dong",
    "TP1_1_6": "destination_sido",
    "TP1_1_7": "destination_sigungu",
}


def _clean(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _fill_from_lookup(
    frame: pd.DataFrame,
    code_column: str,
    lookup: pd.DataFrame,
    target_column: str,
    lookup_column: str,
) -> None:
    """원본 이름이 비어 있을 때만 행정동 표의 이름을 채운다."""

    if target_column not in frame or lookup.empty:
        return
    mapped = frame[code_column].map(lookup[lookup_column])
    missing = frame[target_column].eq("")
    frame.loc[missing, target_column] = mapped[missing].fillna("")


def _scope(row: pd.Series) -> str | pd.NA:
    origin = row["origin_admin_dong"]
    destination = row["destination_admin_dong"]
    origin_sido = row["origin_sido"]
    destination_sido = row["destination_sido"]
    origin_sigungu = row["origin_sigungu"]
    destination_sigungu = row["destination_sigungu"]
    if not origin or not destination:
        return pd.NA
    if origin == destination:
        return "same_dong"
    if origin_sido and origin_sido == destination_sido:
        if origin_sigungu and origin_sigungu == destination_sigungu:
            return "same_sigungu"
        return "same_sido"
    return "inter_sido"


def derive_location_features(
    frame: pd.DataFrame,
    admin_lookup: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Code Book에 정의된 장소 컬럼을 표준 이름과 OD scope로 확장한다."""

    missing = set(LOCATION_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"장소 Feature에 필요한 컬럼이 없음: {sorted(missing)}")

    result = frame.rename(columns=LOCATION_COLUMNS).copy()
    for column in LOCATION_COLUMNS.values():
        result[column] = _clean(result[column])

    if admin_lookup is not None:
        _fill_from_lookup(result, "origin_admin_dong", admin_lookup, "origin_sido", "sido")
        _fill_from_lookup(
            result,
            "origin_admin_dong",
            admin_lookup,
            "origin_sigungu",
            "sigungu",
        )
        _fill_from_lookup(
            result,
            "destination_admin_dong",
            admin_lookup,
            "destination_sido",
            "sido",
        )
        _fill_from_lookup(
            result,
            "destination_admin_dong",
            admin_lookup,
            "destination_sigungu",
            "sigungu",
        )

    result["od_scope"] = result.apply(_scope, axis=1).astype("string")
    return result

