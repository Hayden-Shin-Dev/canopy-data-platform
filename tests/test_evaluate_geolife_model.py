import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier

from scripts.evaluate_geolife_model import evaluate_model


class EvaluateGeoLifeModelTests(unittest.TestCase):
    def test_evaluates_requested_split(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "windows.csv"
            model_path = root / "model.joblib"
            frame = pd.DataFrame(
                {
                    "user_id": ["001", "002", "003"],
                    "split": ["train", "validation", "test"],
                    "canonical_mode": ["walk", "walk", "walk"],
                    "distance_m": [1.0, 2.0, 3.0],
                }
            )
            frame.to_csv(dataset, index=False, encoding="utf-8-sig")
            model = DummyClassifier(strategy="most_frequent").fit([[1.0]], ["walk"])
            joblib.dump({"model": model, "feature_columns": ["distance_m"], "classes": ["walk"]}, model_path)

            result = evaluate_model(dataset, model_path, split="test")

        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["user_count"], 1)
        self.assertEqual(result["accuracy"], 1.0)

    def test_rejects_empty_split(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "windows.csv"
            model_path = root / "model.joblib"
            pd.DataFrame(
                {
                    "user_id": ["001"],
                    "split": ["train"],
                    "canonical_mode": ["walk"],
                    "distance_m": [1.0],
                }
            ).to_csv(dataset, index=False, encoding="utf-8-sig")
            model = DummyClassifier(strategy="most_frequent").fit([[1.0]], ["walk"])
            joblib.dump({"model": model, "feature_columns": ["distance_m"], "classes": ["walk"]}, model_path)

            with self.assertRaises(ValueError):
                evaluate_model(dataset, model_path, split="test")


if __name__ == "__main__":
    unittest.main()
