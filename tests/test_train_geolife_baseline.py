from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.train_geolife_baseline import train_baseline


class GeoLifeBaselineTrainingTests(unittest.TestCase):
    def test_trains_and_writes_metrics(self) -> None:
        rows = []
        modes = ("walk", "bike", "car", "bus", "rail")
        for split in ("train", "validation", "test"):
            for index, mode in enumerate(modes):
                rows.append(
                    {
                        "user_id": f"{split[0]}{index:02d}",
                        "trajectory_id": "sample",
                        "window_start": "2020-01-01 00:00:00",
                        "window_end": "2020-01-01 00:01:00",
                        "canonical_mode": mode,
                        "split": split,
                        "label_coverage": 1.0,
                        "matched_point_count": 2,
                        "ambiguous_point_count": 0,
                        "excluded_point_count": 0,
                        "dominant_mode_point_count": 2,
                        "canonical_mode_purity": 1.0,
                        "distinct_mode_count": 1,
                        "is_transition_window": False,
                        "distance_m": float(index + 1),
                        "mean_speed_mps": float(index + 1),
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.csv"
            model = root / "model.joblib"
            metrics = root / "metrics.json"
            pd.DataFrame(rows).to_csv(dataset, index=False, encoding="utf-8-sig")
            result = train_baseline(dataset, model, metrics, n_estimators=5)
            saved = json.loads(metrics.read_text(encoding="utf-8"))
            model_created = model.exists()

        self.assertTrue(model_created)
        self.assertEqual(result["classes"], sorted(modes))
        self.assertEqual(result["class_weight"], "balanced_subsample")
        self.assertNotIn("canonical_mode_purity", result["feature_columns"])
        self.assertNotIn("is_transition_window", result["feature_columns"])
        self.assertEqual(saved["metrics"]["test"]["row_count"], 5)

    def test_rejects_empty_estimator_count(self) -> None:
        with self.assertRaises(ValueError):
            train_baseline("missing.csv", "model.joblib", "metrics.json", n_estimators=0)

    def test_rejects_unknown_class_weight(self) -> None:
        with self.assertRaises(ValueError):
            train_baseline("missing.csv", "model.joblib", "metrics.json", class_weight="unknown")

    def test_rejects_unknown_model_type(self) -> None:
        with self.assertRaises(ValueError):
            train_baseline("missing.csv", "model.joblib", "metrics.json", model_type="unknown")

    def test_trains_catboost_candidate(self) -> None:
        rows = []
        for split in ("train", "validation", "test"):
            for index, mode in enumerate(("walk", "bike", "car", "bus", "rail")):
                rows.append(
                    {
                        "user_id": f"{split[0]}{index:02d}",
                        "trajectory_id": "sample",
                        "window_start": "2020-01-01 00:00:00",
                        "window_end": "2020-01-01 00:01:00",
                        "canonical_mode": mode,
                        "split": split,
                        "distance_m": float(index + 1),
                        "mean_speed_mps": float(index + 1),
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.csv"
            model = root / "model.joblib"
            metrics = root / "metrics.json"
            pd.DataFrame(rows).to_csv(dataset, index=False, encoding="utf-8-sig")
            result = train_baseline(dataset, model, metrics, n_estimators=5, class_weight=None, model_type="catboost")
            model_created = model.exists()

        self.assertEqual(result["model"], "CatBoostClassifier")
        self.assertTrue(model_created)


if __name__ == "__main__":
    unittest.main()
