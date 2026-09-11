from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.schema import MODEL_FEATURES
from src.validate_dataset import validate_feature_frame


def _valid_frame() -> pd.DataFrame:
    row: dict[str, object] = {
        "trip_id": "idx-1-fid-1",
        "person_group_id": "idx-1",
        "actual_mode_sequence": "car",
        "main_mode_raw_code": "2",
        "survey_date": "2021-10-21",
        "actual_mode": "car",
        "split": "train",
    }
    row.update({column: "값" for column in MODEL_FEATURES})
    row.update(
        {
            "departure_hour": 8,
            "departure_minute_bin": 2,
            "origin_x": 953808.5,
            "origin_y": 1952441.25,
            "destination_x": 954100.0,
            "destination_y": 1953000.0,
            "od_straight_distance_km": None,
            "distance_band": None,
        }
    )
    return pd.DataFrame([row])


def test_validate_feature_frame_accepts_schema_conformant_row() -> None:
    result = validate_feature_frame(_valid_frame())

    assert result == {"row_count": 1, "columns": 26, "status": "valid"}


def test_validate_feature_frame_rejects_unknown_mode() -> None:
    frame = _valid_frame()
    frame.loc[0, "actual_mode"] = "taxi"

    with pytest.raises(ValueError, match="actual_mode"):
        validate_feature_frame(frame)
