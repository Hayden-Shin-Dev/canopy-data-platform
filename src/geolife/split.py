"""GeoLife Window을 user 단위로 train/validation/test에 나눈다."""

from __future__ import annotations

import random
from collections.abc import Mapping

import pandas as pd


DEFAULT_SPLIT_RATIOS: Mapping[str, float] = {
    "train": 0.70,
    "validation": 0.15,
    "test": 0.15,
}


def assign_group_splits(
    frame: pd.DataFrame,
    *,
    group_column: str = "user_id",
    ratios: Mapping[str, float] = DEFAULT_SPLIT_RATIOS,
    seed: int = 2021,
) -> pd.DataFrame:
    """같은 group이 여러 split에 들어가지 않도록 split column을 추가한다."""
    if group_column not in frame.columns:
        raise ValueError(f"group column이 없습니다: {group_column}")
    if set(ratios) != {"train", "validation", "test"}:
        raise ValueError("ratios는 train, validation, test를 모두 가져야 합니다")
    if any(value <= 0 for value in ratios.values()) or abs(sum(ratios.values()) - 1) > 1e-9:
        raise ValueError("split ratio는 양수이고 합이 1이어야 합니다")

    groups = sorted(frame[group_column].astype(str).unique())
    if len(groups) < 3:
        raise ValueError("최소 3개의 group이 필요합니다")
    random.Random(seed).shuffle(groups)
    train_count = max(1, round(len(groups) * ratios["train"]))
    validation_count = max(1, round(len(groups) * ratios["validation"]))
    if train_count + validation_count >= len(groups):
        validation_count = 1
        train_count = len(groups) - 2

    split_by_group: dict[str, str] = {}
    for group in groups[:train_count]:
        split_by_group[group] = "train"
    for group in groups[train_count : train_count + validation_count]:
        split_by_group[group] = "validation"
    for group in groups[train_count + validation_count :]:
        split_by_group[group] = "test"

    result = frame.copy()
    result["split"] = result[group_column].astype(str).map(split_by_group)
    return result

