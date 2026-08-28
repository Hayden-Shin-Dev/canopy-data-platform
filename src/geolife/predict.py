"""저장된 GeoLife baseline으로 Window mode 확률을 계산한다."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd


def predict_probabilities(
    model_path: str | Path,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """학습 artifact의 feature 순서와 class 순서를 사용해 확률을 반환한다."""
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or not {"model", "feature_columns", "classes"} <= set(bundle):
        raise ValueError("GeoLife model artifact 형식이 잘못됐습니다")
    feature_columns = list(bundle["feature_columns"])
    missing = sorted(set(feature_columns) - set(features.columns))
    if missing:
        raise ValueError(f"예측 입력에 필요한 feature가 없습니다: {missing}")
    numeric = features[feature_columns].copy()
    for column in feature_columns:
        numeric[column] = pd.to_numeric(numeric[column], errors="coerce").fillna(0.0)
    probabilities = bundle["model"].predict_proba(numeric)
    result = pd.DataFrame(probabilities, columns=list(bundle["classes"]), index=features.index)
    row_sums = result.sum(axis=1)
    if not ((row_sums - 1.0).abs() < 1e-9).all():
        raise ValueError("예측 확률의 합이 1이 아닙니다")
    return result

