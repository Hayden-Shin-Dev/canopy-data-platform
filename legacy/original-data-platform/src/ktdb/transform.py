"""개인·이동 원본을 모델 입력에 가까운 통행 표로 연결한다."""

from __future__ import annotations

import hashlib

import pandas as pd

from .codebook import Codebook
from .locations import derive_location_features
from .modes import CANOPY_CLASSES, derive_mode_features
from .purpose import derive_commute_direction, derive_purpose
from .time_features import derive_time_features


def _person_group_id(value: object) -> str:
    """원본 idx를 노출하지 않고 그룹 분할용으로 안정적인 ID를 만든다."""

    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def build_feature_frame(
    trips: pd.DataFrame,
    persons: pd.DataFrame,
    codebook: Codebook,
    admin_lookup: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """한 chunk를 조인하고 모든 현재 단계 Feature를 순서대로 파생한다."""

    if "idx" not in trips.columns or "idx" not in persons.columns:
        raise ValueError("개인·이동 표 모두 idx가 필요함")
    if persons["idx"].duplicated().any():
        raise ValueError("개인 표의 idx가 중복됨")

    result = trips.merge(persons[["idx", "DATE"]], on="idx", how="left", validate="many_to_one")
    if result["DATE"].eq("").any():
        raise ValueError("이동 표와 개인 표의 DATE 조인이 완전하지 않음")

    result = derive_time_features(result)
    result = derive_location_features(result, admin_lookup)
    result = derive_purpose(result, codebook)
    result = derive_commute_direction(result)
    result = derive_mode_features(result, codebook)
    result["person_group_id"] = result["idx"].map(_person_group_id)
    result["trip_id"] = result["fid"].astype("string")

    # 대표수단이 POC 대상 5개 class인 행만 downstream 학습 표로 넘긴다.
    result = result[result["actual_mode"].isin(CANOPY_CLASSES)].copy()
    return result.reset_index(drop=True)
