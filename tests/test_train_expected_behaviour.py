from __future__ import annotations

import pandas as pd

from src.ktdb.schema import MODEL_FEATURES
from src.train_expected_behaviour import TrainingConfig, train_expected_behaviour


def test_train_expected_behaviour_saves_artifact_and_metrics(tmp_path) -> None:
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

    artifact = tmp_path / "model.pkl"
    result = train_expected_behaviour(
        pd.DataFrame(rows), artifact, config=TrainingConfig(iterations=5, depth=2)
    )

    assert artifact.exists()
    assert result["backend"] in {"catboost", "sklearn"}
    assert set(result["metrics"]) == {"train", "validation", "test"}
    assert 0 <= result["metrics"]["test"]["macro_f1"] <= 1
