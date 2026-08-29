import joblib
import pandas as pd

from src.integration.expected_behaviour import predict_expected
from src.ktdb.schema import MODEL_FEATURES


def _features():
    return {
        "weekday": "weekday",
        "departure_hour": 8,
        "departure_minute_bin": 2,
        "time_band": "morning_peak",
        "origin_admin_dong": "11110515",
        "origin_x": 126.98,
        "origin_y": 37.57,
        "origin_sido": "서울",
        "origin_sigungu": "종로구",
        "destination_admin_dong": "11110615",
        "destination_x": 126.99,
        "destination_y": 37.58,
        "destination_sido": "서울",
        "destination_sigungu": "종로구",
        "od_scope": "intra_sigungu",
        "od_straight_distance_km": 1.2,
        "distance_band": "0-2km",
        "purpose": "commute",
        "commute_direction": "to_work",
    }


class _StaticClassifier:
    classes_ = ["walk", "car"]

    def predict_proba(self, frame):
        return [[0.75, 0.25] for _ in range(len(frame))]


def test_expected_adapter_preserves_five_mode_probability_contract(tmp_path):
    # The temporary artifact exercises the adapter; production uses the tracked KTDB model path.
    model_path = tmp_path / "ktdb.joblib"
    joblib.dump({"backend": "sklearn", "model": _StaticClassifier()}, model_path)

    result = predict_expected(_features(), model_path=model_path)

    assert set(result.probabilities) == {"walk", "bike", "car", "bus", "rail"}
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-9
    assert result.predicted_mode in {"walk", "bike", "car", "bus", "rail"}
