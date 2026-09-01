from pathlib import Path

import joblib
import pandas as pd

from scripts.train_aihub_model import train_model
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def test_trains_and_persists_aihub_candidate(tmp_path: Path) -> None:
    rows = []
    for split, users in (("train", range(10)), ("validation", range(10, 15)), ("test", range(15, 20))):
        for user in users:
            for index, mode in enumerate(("walk", "bike", "car", "bus", "rail")):
                row = {"user_id": f"u{user}", "canonical_mode": mode, "split": split}
                row.update({column: float(index) for column in AIHUB_FEATURE_COLUMNS})
                rows.append(row)
    dataset = tmp_path / "dataset.csv"
    model_path = tmp_path / "model.joblib"
    metrics = tmp_path / "metrics.json"
    pd.DataFrame(rows).to_csv(dataset, index=False)
    result = train_model(dataset, model_path, metrics, model_type="extra_trees", n_estimators=5)
    assert result["metrics"]["test"]["row_count"] == 25
    assert model_path.is_file()
    assert metrics.is_file()
    assert set(joblib.load(model_path)["classes"]) == {"walk", "bike", "car", "bus", "rail"}
    assert "brier_score" in result["metrics"]["validation"]
    assert len(result["dataset_sha256"]) == 64


def test_validation_calibration_is_recorded_in_artifact(tmp_path: Path) -> None:
    rows = []
    for split, users in (("train", range(10)), ("validation", range(10, 15)), ("test", range(15, 20))):
        for user in users:
            for index, mode in enumerate(("walk", "bike", "car", "bus", "rail")):
                row = {"user_id": f"u{user}", "canonical_mode": mode, "split": split}
                row.update({column: float(index) for column in AIHUB_FEATURE_COLUMNS})
                rows.append(row)
    dataset = tmp_path / "dataset.csv"
    model_path = tmp_path / "model.joblib"
    metrics = tmp_path / "metrics.json"
    pd.DataFrame(rows).to_csv(dataset, index=False)
    result = train_model(
        dataset,
        model_path,
        metrics,
        model_type="hist_gradient_boosting",
        calibrate_validation=True,
    )
    assert len(result["probability_bias"]) == 5
    assert joblib.load(model_path)["probability_bias"] == result["probability_bias"]
