from datetime import datetime, timedelta, timezone

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.integration.geolife_adapter import infer_windows
from src.integration.gps_contract import validate_gps_event


FEATURES = [
    "point_count", "observed_duration_sec", "distance_m", "displacement_m", "straightness_ratio",
    "mean_speed_mps", "max_speed_mps", "speed_std_mps", "mean_abs_acceleration_mps2",
    "acceleration_std_mps2", "stop_ratio", "mean_heading_change_deg", "altitude_range_m",
    "avg_sampling_interval_sec", "valid_step_count", "gap_step_count",
]


def _events():
    start = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    result = []
    for sequence, seconds in enumerate((0, 60, 119, 120, 180)):
        payload = {
            "schema_version": "1.0", "trip_id": "trip-1", "device_id": "device-1", "sequence": sequence,
            "timestamp": (start + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z"),
            "latitude": 37.5665, "longitude": 126.978 + sequence * 0.001,
            "horizontal_accuracy_m": 5, "altitude_m": 30, "vertical_accuracy_m": 5,
            "speed_mps": 2, "course_deg": 90,
        }
        checked = validate_gps_event(payload)
        assert checked.event is not None
        result.append(checked.event)
    return result


def test_existing_geolife_window_features_and_probability_contract_are_used(tmp_path):
    model = RandomForestClassifier(n_estimators=2, random_state=1).fit(
        pd.DataFrame([[0] * len(FEATURES), [1] * len(FEATURES)]), ["walk", "car"]
    )
    model_path = tmp_path / "geolife.joblib"
    joblib.dump({"model": model, "feature_columns": FEATURES, "classes": ["walk", "car"]}, model_path)

    windows = infer_windows(_events(), model_path=model_path)

    assert len(windows) == 2
    assert windows[0].status == "READY"
    assert windows[0].predicted_mode in {"walk", "car"}
    assert abs(sum(windows[0].probabilities.values()) - 1.0) < 1e-9
    assert windows[1].status == "COLLECTING"


def test_aihub_artifact_is_opt_in_backend_for_same_window_interface(tmp_path):
    from src.aihub.features import AIHUB_FEATURE_COLUMNS

    model = RandomForestClassifier(n_estimators=2, random_state=1).fit(
        pd.DataFrame([[0] * len(AIHUB_FEATURE_COLUMNS), [1] * len(AIHUB_FEATURE_COLUMNS)]),
        ["walk", "car"],
    )
    model_path = tmp_path / "aihub.joblib"
    joblib.dump(
        {
            "model": model,
            "feature_columns": list(AIHUB_FEATURE_COLUMNS),
            "classes": ["walk", "car"],
            "feature_version": "aihub-window-v1",
            "window_duration_seconds": 60,
        },
        model_path,
    )

    windows = infer_windows(_events(), model_path=model_path, window_seconds=60)

    assert len(windows) >= 1
    assert windows[0].status == "READY"
    assert windows[0].predicted_mode in {"walk", "car"}
