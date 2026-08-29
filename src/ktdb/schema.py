"""KTDB 원본에서 읽을 컬럼과 최종 Feature 이름을 한 곳에 모은다."""

from __future__ import annotations


PERSON_COLUMNS: tuple[str, ...] = ("idx", "DATE")

TRIP_BASE_COLUMNS: tuple[str, ...] = (
    "idx",
    "fid",
    "th_seq",
    "sTP1",
    "sTP1_1_4",
    "sTP1_1_5",
    "sTP1_1_6",
    "sTP1_1_7",
    "sTP1_1_8",
    "TP1",
    "TP1_1_4",
    "TP1_1_5",
    "TP1_1_6",
    "TP1_1_7",
    "TP1_1_8",
    "TP2",
    "TP2_a",
    "TP3_1",
    "TP3_2",
    "TP4_1",
    "TP4_2",
)


MODEL_FEATURES: tuple[str, ...] = (
    "weekday",
    "departure_hour",
    "departure_minute_bin",
    "time_band",
    "origin_admin_dong",
    "origin_x",
    "origin_y",
    "origin_sido",
    "origin_sigungu",
    "destination_admin_dong",
    "destination_x",
    "destination_y",
    "destination_sido",
    "destination_sigungu",
    "od_scope",
    "od_straight_distance_km",
    "distance_band",
    "purpose",
    "commute_direction",
)


def trip_columns(mode_count: int = 10) -> tuple[str, ...]:
    """기본 통행 컬럼 뒤에 TP5 이동수단과 소요시간을 붙여 반환한다."""

    if not 1 <= mode_count <= 10:
        raise ValueError("mode_count는 1부터 10 사이여야 함")

    columns = list(TRIP_BASE_COLUMNS)
    for number in range(1, mode_count + 1):
        columns.extend((f"TP5_{number}", f"TP5_{number}_t1"))
    return tuple(columns)

