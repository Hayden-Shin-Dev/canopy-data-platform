"""Population Feature CSV를 모델 입력 X/y로 정리하는 모듈."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .schema import MODEL_FEATURES


TARGET_COLUMN = "actual_mode"
NUMERIC_FEATURES: tuple[str, ...] = (
    "departure_hour",
    "departure_minute_bin",
    "od_straight_distance_km",
)
CATEGORICAL_FEATURES: tuple[str, ...] = tuple(
    column for column in MODEL_FEATURES if column not in NUMERIC_FEATURES
)
FORBIDDEN_MODEL_COLUMNS: tuple[str, ...] = (
    "trip_id",
    "person_group_id",
    "survey_date",
    "actual_mode_sequence",
    "main_mode_raw_code",
)


@dataclass(frozen=True)
class ModelData:
    """모델 학습에 필요한 변환 결과와 feature 타입 정보를 함께 보관한다."""

    features: pd.DataFrame
    target: pd.Series
    categorical_features: tuple[str, ...]
    numeric_features: tuple[str, ...]


def prepare_model_data(frame: pd.DataFrame) -> ModelData:
    """승인된 feature만 남기고 CatBoost 입력에 맞게 결측값을 정리한다."""

    required = set(MODEL_FEATURES) | {TARGET_COLUMN, "split"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"모델 입력에 필요한 컬럼이 없습니다: {missing}")
    invalid_target = sorted(set(frame[TARGET_COLUMN].dropna().astype(str)) - {"walk", "bike", "car", "bus", "rail"})
    if invalid_target:
        raise ValueError(f"지원하지 않는 target class가 있습니다: {invalid_target}")

    features = _prepare_features(frame)
    target = frame[TARGET_COLUMN].astype("string")
    return ModelData(
        features=features,
        target=target,
        categorical_features=CATEGORICAL_FEATURES,
        numeric_features=NUMERIC_FEATURES,
    )


def _prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    """학습과 예측에서 공유하는 feature dtype 정리."""

    features = frame[list(MODEL_FEATURES)].copy()
    for column in NUMERIC_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce")
    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].astype("string").fillna("<missing>").astype(str)
    return features


def prepare_prediction_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, tuple[str, ...], tuple[str, ...]]:
    """target와 split 없이 들어온 새 관측치를 모델 입력으로 변환한다."""

    missing = sorted(set(MODEL_FEATURES) - set(frame.columns))
    if missing:
        raise ValueError(f"예측 입력에 필요한 feature 컬럼이 없습니다: {missing}")
    return _prepare_features(frame), CATEGORICAL_FEATURES, NUMERIC_FEATURES


def split_model_data(frame: pd.DataFrame) -> dict[str, ModelData]:
    """split 컬럼을 기준으로 독립적인 train/validation/test 입력을 만든다."""

    if "split" not in frame.columns:
        raise ValueError("split 컬럼이 없습니다")
    result: dict[str, ModelData] = {}
    for split_name in ("train", "validation", "test"):
        subset = frame[frame["split"].eq(split_name)].copy()
        if subset.empty:
            continue
        result[split_name] = prepare_model_data(subset)
    return result
