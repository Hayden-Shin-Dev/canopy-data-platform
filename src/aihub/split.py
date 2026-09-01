"""Deterministic user-disjoint splits for AI-Hub trajectory tables."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

import pandas as pd


DEFAULT_RATIOS: Mapping[str, float] = {"train": 0.70, "validation": 0.15, "test": 0.15}


class AiHubSplitError(ValueError):
    """Raised when a user-disjoint split cannot be constructed safely."""


def _group_order(groups: list[str], seed: int) -> list[str]:
    return sorted(groups, key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())


def assign_user_splits(
    frame: pd.DataFrame,
    *,
    group_column: str = "user_id",
    target_column: str = "canonical_mode",
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = 2021,
) -> pd.DataFrame:
    """Assign every user to exactly one split while keeping class coverage."""

    required = {group_column, target_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise AiHubSplitError(f"Missing split columns: {missing}")
    if set(ratios) != {"train", "validation", "test"} or abs(sum(ratios.values()) - 1.0) > 1e-9:
        raise AiHubSplitError("ratios must contain train, validation, test and sum to one")
    if any(value <= 0 for value in ratios.values()):
        raise AiHubSplitError("split ratios must be positive")

    groups = frame[group_column].astype(str)
    if groups.nunique() < 3:
        raise AiHubSplitError("At least three users are required")
    group_rows = frame.assign(_group=groups).groupby("_group", sort=False)
    group_sizes = group_rows.size().to_dict()
    group_classes = {
        str(group): set(part[target_column].astype(str))
        for group, part in group_rows
    }
    ordered = sorted(_group_order(list(group_sizes), seed), key=lambda group: -group_sizes[group])
    total_rows = len(frame)
    target_rows = {split: total_rows * ratio for split, ratio in ratios.items()}
    assigned_rows = {split: 0 for split in ratios}
    assigned_classes = {split: set() for split in ratios}
    split_by_group: dict[str, str] = {}

    for group in ordered:
        candidates = []
        for split in ratios:
            projected = assigned_rows[split] + group_sizes[group]
            size_error = abs(projected - target_rows[split]) / max(target_rows[split], 1)
            missing_class_penalty = len(group_classes[group] - assigned_classes[split])
            candidates.append((size_error + 0.05 * missing_class_penalty, split))
        _, selected = min(candidates)
        split_by_group[group] = selected
        assigned_rows[selected] += group_sizes[group]
        assigned_classes[selected].update(group_classes[group])

    result = frame.copy()
    result["split"] = groups.map(split_by_group)
    expected_classes = set(frame[target_column].astype(str))
    for split, classes in assigned_classes.items():
        if classes != expected_classes:
            raise AiHubSplitError(
                f"{split} split does not contain every class: missing={sorted(expected_classes - classes)}"
            )
    return result


def split_manifest(frame: pd.DataFrame, *, group_column: str = "user_id") -> dict[str, object]:
    if "split" not in frame.columns or group_column not in frame.columns:
        raise AiHubSplitError("A split column and group column are required")
    users = frame[[group_column, "split"]].drop_duplicates()
    if users[group_column].duplicated().any():
        raise AiHubSplitError("A user appears in more than one split")
    return {
        "group_column": group_column,
        "user_count": int(users[group_column].nunique()),
        "split_user_counts": {
            str(split): int((users["split"] == split).sum())
            for split in ("train", "validation", "test")
        },
        "groups": [
            {"user_id": str(row[group_column]), "split": str(row["split"])}
            for _, row in users.sort_values(group_column).iterrows()
        ],
    }
