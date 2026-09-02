"""Opt-in runtime adapter for the AI-Hub 60-second model contract."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from datetime import timedelta

import joblib
import pandas as pd

from src.integration.gps_contract import GpsEvent

from .features import AIHUB_FEATURE_COLUMNS, canonical_window_features
from .ingest import AiHubPoint
from .training import BASE_FEATURE_COLUMNS, ROBUST_FEATURE_COLUMNS
from .training import _biased_probabilities
def _event_points(events: Sequence[GpsEvent]) -> list[AiHubPoint]:
    return [
        AiHubPoint(
            timestamp=event.timestamp.replace(tzinfo=None),
            latitude=event.latitude,
            longitude=event.longitude,
            accuracy_m=event.horizontal_accuracy_m,
            altitude_m=event.altitude_m,
        )
        for event in events
    ]


def event_features(events: Sequence[GpsEvent]) -> dict[str, float | int]:
    if len(events) < 2:
        raise ValueError("At least two GPS events are required")
    return canonical_window_features(
        _event_points(events),
        user_id=events[0].device_id,
        trajectory_id=events[0].trip_id,
        raw_point_count=len(events),
    )


def latest_rolling_window(
    events: Sequence[GpsEvent],
    *,
    window_seconds: int = 120,
    stride_seconds: int = 10,
) -> tuple[int, list[GpsEvent]] | None:
    """완료된 최신 120초 구간을 10초 간격으로 골라낸다."""

    if window_seconds <= 0 or stride_seconds <= 0:
        raise ValueError("window_seconds and stride_seconds must be positive")
    if len(events) < 2:
        return None
    ordered = sorted(events, key=lambda event: event.timestamp)
    anchor = ordered[0].timestamp
    elapsed = (ordered[-1].timestamp - anchor).total_seconds()
    if elapsed < window_seconds:
        return None
    slot = int((elapsed - window_seconds) // stride_seconds)
    start = anchor + timedelta(seconds=slot * stride_seconds)
    end = start + timedelta(seconds=window_seconds)
    selected = [event for event in ordered if start <= event.timestamp < end]
    return (slot, selected) if len(selected) >= 2 else None


def predict_event_window(model_path: str | Path, events: Sequence[GpsEvent]) -> dict[str, object]:
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or not {"model", "feature_columns", "classes"} <= set(bundle):
        raise ValueError("Invalid AI-Hub model artifact")
    allowed_feature_sets = {
        tuple(AIHUB_FEATURE_COLUMNS),
        tuple(BASE_FEATURE_COLUMNS),
        tuple(ROBUST_FEATURE_COLUMNS),
    }
    if tuple(bundle["feature_columns"]) not in allowed_feature_sets:
        raise ValueError("AI-Hub model feature contract does not match runtime")
    duration_seconds = (events[-1].timestamp - events[0].timestamp).total_seconds()
    expected_duration = float(bundle.get("window_duration_seconds", 60))
    if duration_seconds < expected_duration * 0.75:
        return {
            "status": "COLLECTING",
            "predicted_mode": None,
            "confidence": None,
            "probabilities": {},
            "feature_version": bundle.get("feature_version", "unknown"),
            "window_duration_seconds": duration_seconds,
        }
    frame = pd.DataFrame([event_features(events)])[list(bundle["feature_columns"])]
    classes = [str(value) for value in bundle["classes"]]
    probabilities = bundle["model"].predict_proba(frame)
    probabilities = _biased_probabilities(
        probabilities,
        classes,
        bundle.get("probability_bias"),
    )[0]
    probability_map = {classes[index]: float(value) for index, value in enumerate(probabilities)}
    predicted_mode = max(probability_map, key=probability_map.get)
    return {
        "predicted_mode": predicted_mode,
        "confidence": probability_map[predicted_mode],
        "probabilities": probability_map,
        "feature_version": bundle.get("feature_version", "unknown"),
        "status": "READY",
        "window_duration_seconds": duration_seconds,
    }
