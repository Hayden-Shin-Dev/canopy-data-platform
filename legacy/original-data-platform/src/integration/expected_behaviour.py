"""Adapter for the production KTDB Expected Behaviour model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.ktdb.schema import MODEL_FEATURES
from src.predict_expected_behaviour import DEFAULT_MODEL, predict_expected_behaviour


@dataclass(frozen=True)
class ExpectedBehaviourResult:
    probabilities: dict[str, float]
    predicted_mode: str


def predict_expected(
    features: Mapping[str, object],
    *,
    model_path: str | Path = DEFAULT_MODEL,
) -> ExpectedBehaviourResult:
    """Run the KTDB model with its complete production feature contract."""

    missing = sorted(set(MODEL_FEATURES) - set(features))
    if missing:
        raise ValueError(f"KTDB Expected Behaviour inputs missing: {missing}")
    frame = pd.DataFrame([{name: features[name] for name in MODEL_FEATURES}])
    prediction = predict_expected_behaviour(frame, model_path=model_path).iloc[0]
    probabilities = {mode: float(prediction[f"{mode}_probability"]) for mode in ("walk", "bike", "car", "bus", "rail")}
    return ExpectedBehaviourResult(probabilities=probabilities, predicted_mode=str(prediction["predicted_mode"]))
