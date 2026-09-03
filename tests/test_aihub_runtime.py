from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import ExtraTreesClassifier

from src.aihub.features import AIHUB_FEATURE_COLUMNS
from src.aihub.runtime import _MODEL_CACHE, latest_rolling_window, predict_event_window
from src.integration.gps_contract import GpsEvent


def _event(index: int) -> GpsEvent:
    return GpsEvent(
        schema_version="1.0",
        trip_id="trip",
        device_id="device",
        sequence=index,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index),
        latitude=37.5 + index * 0.0001,
        longitude=126.9 + index * 0.0001,
        horizontal_accuracy_m=5.0,
        altitude_m=10.0,
        vertical_accuracy_m=5.0,
        speed_mps=1.0,
        course_deg=45.0,
    )


def test_runtime_uses_same_feature_contract(tmp_path: Path) -> None:
    model = ExtraTreesClassifier(n_estimators=2, random_state=1).fit(
        [[0.0] * len(AIHUB_FEATURE_COLUMNS), [1.0] * len(AIHUB_FEATURE_COLUMNS)],
        ["walk", "car"],
    )
    path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "feature_columns": list(AIHUB_FEATURE_COLUMNS), "classes": ["walk", "car"], "feature_version": "aihub-window-v1"}, path)
    result = predict_event_window(path, [_event(index) for index in range(61)])
    assert result["predicted_mode"] in {"walk", "car"}
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-9


def test_runtime_reuses_unchanged_model_artifact(tmp_path: Path, monkeypatch) -> None:
    model = ExtraTreesClassifier(n_estimators=2, random_state=1).fit(
        [[0.0] * len(AIHUB_FEATURE_COLUMNS), [1.0] * len(AIHUB_FEATURE_COLUMNS)],
        ["walk", "car"],
    )
    path = tmp_path / "cached-model.joblib"
    joblib.dump({"model": model, "feature_columns": list(AIHUB_FEATURE_COLUMNS), "classes": ["walk", "car"]}, path)
    real_load = joblib.load
    calls: list[Path] = []

    def counted_load(candidate):
        calls.append(Path(candidate))
        return real_load(candidate)

    _MODEL_CACHE.clear()
    monkeypatch.setattr("src.aihub.runtime.joblib.load", counted_load)
    events = [_event(index) for index in range(61)]

    predict_event_window(path, events)
    predict_event_window(path, events)

    assert calls == [path]


def test_runtime_waits_for_a_complete_aihub_window(tmp_path: Path) -> None:
    model = ExtraTreesClassifier(n_estimators=2, random_state=1).fit(
        [[0.0] * len(AIHUB_FEATURE_COLUMNS), [1.0] * len(AIHUB_FEATURE_COLUMNS)],
        ["walk", "car"],
    )
    path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "feature_columns": list(AIHUB_FEATURE_COLUMNS), "classes": ["walk", "car"]}, path)
    result = predict_event_window(path, [_event(0), _event(1)])
    assert result["status"] == "COLLECTING"
    assert result["predicted_mode"] is None


def test_runtime_selects_120_second_history_every_10_seconds() -> None:
    events = [_event(index) for index in range(131)]

    rolling = latest_rolling_window(events, window_seconds=120, stride_seconds=10)

    assert rolling is not None
    slot, selected = rolling
    assert slot == 1
    assert selected[0].timestamp == events[10].timestamp
    assert selected[-1].timestamp == events[129].timestamp
    assert len(selected) == 120


def test_runtime_handles_irregular_callback_cadence() -> None:
    events = [_event(index) for index in (0, 7, 19, 45, 91, 121, 137)]

    rolling = latest_rolling_window(events, window_seconds=120, stride_seconds=10)

    assert rolling is not None
    assert rolling[0] == 1
    assert [event.sequence for event in rolling[1]] == [19, 45, 91, 121]


def test_runtime_features_support_missing_accuracy_and_altitude() -> None:
    from dataclasses import replace
    from src.aihub.runtime import event_features

    events = [
        replace(_event(index), horizontal_accuracy_m=None, altitude_m=None)
        for index in range(3)
    ]

    features = event_features(events)

    assert features["accuracy_missing_ratio"] == 1
    assert features["altitude_missing_ratio"] == 1
    assert features["accuracy_mean_m"] == 0
