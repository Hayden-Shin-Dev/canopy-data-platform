"""통행목적을 Code Book 레이블로 바꾸고 출퇴근 방향을 판정한다."""

from __future__ import annotations

import pandas as pd

from .codebook import Codebook, normalize_code


COMMUTE_DIRECTIONS = ("to_work", "work_to_home")


def derive_purpose(frame: pd.DataFrame, codebook: Codebook) -> pd.DataFrame:
    """TP2 코드에 대응하는 Code Book 레이블을 ``purpose``로 추가한다."""

    if "TP2" not in frame.columns:
        raise ValueError("통행목적 컬럼 TP2가 없음")
    result = frame.copy()
    purpose_values = codebook.values_for("TP2")
    result["purpose"] = result["TP2"].map(
        lambda value: purpose_values.get(normalize_code(value), "")
    ).astype("string")
    return result


def derive_commute_direction(frame: pd.DataFrame) -> pd.DataFrame:
    """집→직장과 직장→집을 장소 코드까지 확인해 분류한다."""

    required = {"TP2", "sTP1", "TP1"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"출퇴근 판정에 필요한 컬럼이 없음: {sorted(missing)}")

    result = frame.copy()
    purpose = result["TP2"].map(normalize_code)
    origin = result["sTP1"].map(normalize_code)
    destination = result["TP1"].map(normalize_code)
    result["commute_direction"] = "non_commute"
    result.loc[(purpose == "3") & (origin == "1") & (destination == "2"), "commute_direction"] = "to_work"
    result.loc[(purpose == "1") & (origin == "2") & (destination == "1"), "commute_direction"] = "work_to_home"
    result["commute_direction"] = result["commute_direction"].astype("string")
    return result


def filter_commute(frame: pd.DataFrame) -> pd.DataFrame:
    """출퇴근 두 방향만 남긴 새 DataFrame을 반환한다."""

    if "commute_direction" not in frame.columns:
        raise ValueError("commute_direction을 먼저 만들어야 함")
    return frame[frame["commute_direction"].isin(COMMUTE_DIRECTIONS)].copy()

