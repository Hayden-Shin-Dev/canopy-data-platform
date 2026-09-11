from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.model_data import (
    CATEGORICAL_FEATURES,
    FORBIDDEN_MODEL_COLUMNS,
    NUMERIC_FEATURES,
    prepare_model_data,
    split_model_data,
)
from src.ktdb.schema import MODEL_FEATURES


def _frame() -> pd.DataFrame:
    values: dict[str, object] = {column: ["값", "다른값"] for column in MODEL_FEATURES}
    values.update(
        {
            "departure_hour": [8, 18],
            "departure_minute_bin": [2, 3],
            "origin_x": [953808.5, None],
            "origin_y": [1952441.25, None],
            "destination_x": [954100.0, 953808.5],
            "destination_y": [1953000.0, 1952441.25],
            "od_straight_distance_km": [None, 4.5],
            "actual_mode": ["car", "walk"],
            "split": ["train", "test"],
            "trip_id": ["t1", "t2"],
            "person_group_id": ["p1", "p2"],
        }
    )
    return pd.DataFrame(values)


def test_prepare_model_data_excludes_identifiers_and_types_features() -> None:
    result = prepare_model_data(_frame())

    assert list(result.features.columns) == list(MODEL_FEATURES)
    assert not set(FORBIDDEN_MODEL_COLUMNS) & set(result.features.columns)
    assert result.categorical_features == CATEGORICAL_FEATURES
    assert result.numeric_features == NUMERIC_FEATURES
    assert result.features.loc[0, "origin_x"] == 953808.5
    assert result.features.loc[0, "od_straight_distance_km"] != result.features.loc[0, "od_straight_distance_km"]


def test_split_model_data_preserves_split_boundaries() -> None:
    result = split_model_data(_frame())

    assert set(result) == {"train", "test"}
    assert list(result["train"].target) == ["car"]
    assert list(result["test"].target) == ["walk"]


def test_prepare_model_data_rejects_unknown_target() -> None:
    frame = _frame()
    frame.loc[0, "actual_mode"] = "taxi"

    with pytest.raises(ValueError, match="target class"):
        prepare_model_data(frame)
