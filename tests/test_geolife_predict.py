from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.geolife.predict import predict_probabilities


class GeoLifePredictionTests(unittest.TestCase):
    def test_returns_five_mode_probabilities_that_sum_to_one(self) -> None:
        feature_columns = ["distance_m", "mean_speed_mps"]
        train_features = pd.DataFrame(
            [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]],
            columns=feature_columns,
        )
        model = RandomForestClassifier(n_estimators=3, random_state=1).fit(
            train_features,
            ["walk", "bike", "car", "bus", "rail"],
        )
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.joblib"
            joblib.dump(
                {"model": model, "feature_columns": feature_columns, "classes": list(model.classes_)},
                model_path,
            )
            result = predict_probabilities(model_path, pd.DataFrame([[1.5, 1.5]], columns=feature_columns))

        self.assertEqual(set(result.columns), {"walk", "bike", "car", "bus", "rail"})
        self.assertAlmostEqual(float(result.sum(axis=1).iloc[0]), 1.0)

    def test_rejects_missing_feature(self) -> None:
        with self.assertRaises(FileNotFoundError):
            predict_probabilities("missing.joblib", pd.DataFrame({"distance_m": [1.0]}))


if __name__ == "__main__":
    unittest.main()
