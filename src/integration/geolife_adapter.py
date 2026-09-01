"""Adapt canonical GPS events to the existing GeoLife window/model pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd
import joblib

from src.config import PROJECT_ROOT
from src.geolife.predict import predict_probabilities
from src.geolife.raw import TrajectoryPoint
from src.geolife.window_features import compute_window_features
from src.geolife.windows import TimeWindow, iter_time_windows

from .gps_contract import GpsEvent


DEFAULT_GEOLIFE_MODEL = PROJECT_ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"


@dataclass(frozen=True)
class WindowInference:
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    status: str
    features: dict[str, float | int]
    probabilities: dict[str, float]
    predicted_mode: str | None
    confidence: float | None


def _to_point(event: GpsEvent) -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id=event.device_id,
        trajectory_id=event.trip_id,
        latitude=event.latitude,
        longitude=event.longitude,
        altitude_ft=(event.altitude_m or 0.0) / 0.3048,
        timestamp=event.timestamp,
    )


def build_window_table(events: Sequence[GpsEvent], *, window_seconds: int = 120) -> list[tuple[TimeWindow, dict[str, float | int]]]:
    """Create features with the repository's GeoLife functions, preserving event order."""

    if len(events) < 2:
        return []
    points = [_to_point(event) for event in events]
    windows = list(iter_time_windows(points, window_seconds=window_seconds, min_points=2))
    return [(window, compute_window_features(window.points)) for window in windows]


def _infer_aihub_windows(
    events: Sequence[GpsEvent],
    *,
    model_path: Path,
    window_seconds: int,
) -> list[WindowInference]:
    """Run the opt-in AI-Hub contract without changing the GeoLife default."""
    from src.aihub.runtime import event_features

    bundle = joblib.load(model_path)
    feature_columns = list(bundle["feature_columns"])
    classes = [str(value) for value in bundle["classes"]]
    expected_seconds = int(bundle.get("window_duration_seconds", window_seconds))
    if expected_seconds != window_seconds:
        raise ValueError(
            f"AI-Hub artifact requires {expected_seconds}s windows; received {window_seconds}s"
        )
    points = [_to_point(event) for event in events]
    windows = list(iter_time_windows(points, window_seconds=window_seconds, min_points=2))
    if not windows:
        return []
    last_timestamp = events[-1].timestamp
    output: list[WindowInference] = []
    for window in windows:
        window_events = [
            event for event in events
            if window.window_start <= event.timestamp < window.window_end
        ]
        if not window_events:
            continue
        features = event_features(window_events)
        frame = pd.DataFrame([features])[feature_columns]
        probabilities = bundle["model"].predict_proba(frame)[0]
        probability_map = {
            classes[index]: float(value) for index, value in enumerate(probabilities)
        }
        closed = last_timestamp >= window.window_end
        predicted = max(probability_map, key=probability_map.get) if closed else None
        output.append(
            WindowInference(
                window_start=pd.Timestamp(window.window_start),
                window_end=pd.Timestamp(window.window_end),
                status="READY" if closed else "COLLECTING",
                features=features,
                probabilities=probability_map,
                predicted_mode=predicted,
                confidence=probability_map[predicted] if predicted else None,
            )
        )
    return output


def infer_windows(
    events: Sequence[GpsEvent],
    *,
    model_path: str | Path = DEFAULT_GEOLIFE_MODEL,
    window_seconds: int = 120,
) -> list[WindowInference]:
    """Infer every closed window; keep incomplete windows explicitly COLLECTING."""

    model = Path(model_path)
    if not model.is_file():
        raise FileNotFoundError(f"GeoLife model artifact not found: {model}")
    try:
        contract = joblib.load(model)
    except Exception:
        contract = None
    if isinstance(contract, dict) and str(contract.get("feature_version", "")).startswith("aihub-window-v1"):
        return _infer_aihub_windows(events, model_path=model, window_seconds=window_seconds)
    built = build_window_table(events, window_seconds=window_seconds)
    if not built:
        return []
    last_timestamp = events[-1].timestamp
    feature_frame = pd.DataFrame([features for _, features in built])
    probability_frame = predict_probabilities(model, feature_frame)
    output: list[WindowInference] = []
    for index, (window, features) in enumerate(built):
        closed = last_timestamp >= window.window_end or index < len(built) - 1
        probabilities = {str(key): float(value) for key, value in probability_frame.iloc[index].to_dict().items()}
        if closed:
            predicted = max(probabilities, key=probabilities.get)
            confidence = probabilities[predicted]
            status = "READY"
        else:
            predicted = None
            confidence = None
            status = "COLLECTING"
        output.append(
            WindowInference(
                window_start=pd.Timestamp(window.window_start),
                window_end=pd.Timestamp(window.window_end),
                status=status,
                features=features,
                probabilities=probabilities,
                predicted_mode=predicted,
                confidence=confidence,
            )
        )
    return output
