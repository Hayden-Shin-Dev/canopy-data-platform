"""Opt-in runtime adapter for the AI-Hub 60-second model contract."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import joblib
import pandas as pd

from src.integration.gps_contract import GpsEvent

from .features import AIHUB_FEATURE_COLUMNS, _std
from .training import _evaluate
from src.geolife.raw import TrajectoryPoint
from src.geolife.window_features import compute_window_features


def _event_points(events: Sequence[GpsEvent]) -> list[TrajectoryPoint]:
    return [
        TrajectoryPoint(
            user_id=event.device_id,
            trajectory_id=event.trip_id,
            latitude=event.latitude,
            longitude=event.longitude,
            altitude_ft=(event.altitude_m or 0.0) / 0.3048,
            timestamp=event.timestamp.replace(tzinfo=None),
        )
        for event in events
    ]


def event_features(events: Sequence[GpsEvent]) -> dict[str, float | int]:
    if len(events) < 2:
        raise ValueError("At least two GPS events are required")
    points = _event_points(events)
    features = dict(compute_window_features(points))
    accuracy = [event.horizontal_accuracy_m for event in events if event.horizontal_accuracy_m is not None]
    altitude_missing = sum(event.altitude_m is None for event in events)
    features.update(
        {
            "accuracy_mean_m": sum(accuracy) / len(accuracy) if accuracy else 0.0,
            "accuracy_std_m": _std([float(value) for value in accuracy]),
            "accuracy_missing_ratio": 1 - len(accuracy) / len(events),
            "altitude_missing_ratio": altitude_missing / len(events),
            "valid_point_ratio": 1.0,
        }
    )
    return features


def predict_event_window(model_path: str | Path, events: Sequence[GpsEvent]) -> dict[str, object]:
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or not {"model", "feature_columns", "classes"} <= set(bundle):
        raise ValueError("Invalid AI-Hub model artifact")
    if list(bundle["feature_columns"]) != list(AIHUB_FEATURE_COLUMNS):
        raise ValueError("AI-Hub model feature contract does not match runtime")
    frame = pd.DataFrame([event_features(events)])[list(AIHUB_FEATURE_COLUMNS)]
    probabilities = bundle["model"].predict_proba(frame)[0]
    classes = [str(value) for value in bundle["classes"]]
    probability_map = {classes[index]: float(value) for index, value in enumerate(probabilities)}
    predicted_mode = max(probability_map, key=probability_map.get)
    return {
        "predicted_mode": predicted_mode,
        "confidence": probability_map[predicted_mode],
        "probabilities": probability_map,
        "feature_version": bundle.get("feature_version", "unknown"),
        "window_duration_seconds": (events[-1].timestamp - events[0].timestamp).total_seconds(),
    }
