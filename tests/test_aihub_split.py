import pandas as pd
import pytest

from src.aihub.split import AiHubSplitError, assign_user_splits, split_manifest


def _frame() -> pd.DataFrame:
    rows = []
    for user in range(30):
        for mode in ("walk", "bike", "car", "bus", "rail"):
            rows.append({"user_id": f"u{user:02d}", "canonical_mode": mode})
    return pd.DataFrame(rows)


def test_user_split_is_disjoint_and_class_complete() -> None:
    result = assign_user_splits(_frame(), seed=7)
    by_user = result.groupby("user_id")["split"].nunique()
    assert by_user.max() == 1
    assert set(result["split"]) == {"train", "validation", "test"}
    for split in ("train", "validation", "test"):
        assert set(result.loc[result["split"] == split, "canonical_mode"]) == {"walk", "bike", "car", "bus", "rail"}
    assert split_manifest(result)["user_count"] == 30


def test_split_requires_enough_users() -> None:
    with pytest.raises(AiHubSplitError):
        assign_user_splits(pd.DataFrame([{"user_id": "u1", "canonical_mode": "walk"}] * 3))
