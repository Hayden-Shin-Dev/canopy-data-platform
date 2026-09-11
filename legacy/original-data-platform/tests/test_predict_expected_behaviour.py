from __future__ import annotations

import pandas as pd

from src.ktdb.schema import MODEL_FEATURES
from src.predict_expected_behaviour import predict_expected_behaviour
from src.train_expected_behaviour import TrainingConfig, train_expected_behaviour


def _frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(15):
        row = {column: f"값-{index % 3}" for column in MODEL_FEATURES}
        row.update(
            {
                "departure_hour": index % 5,
                "departure_minute_bin": index % 4,
                "od_straight_distance_km": float(index),
                "actual_mode": ("car", "walk", "bus")[index % 3],
                "split": "train" if index < 9 else "validation" if index < 12 else "test",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def test_predict_expected_behaviour_returns_five_probabilities(tmp_path) -> None:
    frame = _frame()
    artifact = tmp_path / "model.pkl"
    train_expected_behaviour(frame, artifact, config=TrainingConfig(iterations=5, depth=2))

    inference_frame = frame.iloc[:2].drop(columns=["actual_mode", "split"])
    predictions = predict_expected_behaviour(inference_frame, artifact)

    assert len(predictions) == 2
    assert all(f"{mode}_probability" in predictions for mode in ("walk", "bike", "car", "bus", "rail"))
    assert predictions["predicted_mode"].isin(("walk", "bike", "car", "bus", "rail")).all()
    assert (predictions[[f"{mode}_probability" for mode in ("walk", "bike", "car", "bus", "rail")]].sum(axis=1) > 0.99).all()
