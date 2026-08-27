"""개인 그룹 단위로 재현 가능한 train/validation/test split을 만든다."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

import pandas as pd

from src.config import RANDOM_SEED, SPLIT_RATIOS


def split_for_group(
    group_id: object,
    *,
    seed: int = RANDOM_SEED,
    ratios: Mapping[str, float] = SPLIT_RATIOS,
) -> str:
    """그룹 문자열의 SHA256 일부를 이용해 split 이름을 반환한다."""

    if set(ratios) != {"train", "validation", "test"}:
        raise ValueError("ratios에는 train, validation, test가 모두 있어야 함")
    if abs(sum(ratios.values()) - 1.0) > 1e-9 or any(value <= 0 for value in ratios.values()):
        raise ValueError("split 비율은 양수이고 합이 1이어야 함")

    digest = hashlib.sha256(f"{seed}:{group_id}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    train_end = ratios["train"]
    validation_end = train_end + ratios["validation"]
    if bucket < train_end:
        return "train"
    if bucket < validation_end:
        return "validation"
    return "test"


def assign_group_split(
    frame: pd.DataFrame,
    group_column: str = "person_group_id",
    *,
    seed: int = RANDOM_SEED,
    ratios: Mapping[str, float] = SPLIT_RATIOS,
) -> pd.Series:
    """DataFrame의 각 행에 그룹 기준 split을 붙인다."""

    if group_column not in frame.columns:
        raise ValueError(f"그룹 컬럼이 없음: {group_column}")
    return frame[group_column].map(lambda value: split_for_group(value, seed=seed, ratios=ratios)).astype("string")

