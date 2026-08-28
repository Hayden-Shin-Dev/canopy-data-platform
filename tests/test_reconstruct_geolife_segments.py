import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier

from scripts.reconstruct_geolife_segments import reconstruct_segments


class ReconstructGeoLifeSegmentsTests(unittest.TestCase):
    def test_reconstructs_consecutive_predictions_per_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "windows.csv"
            model_path = root / "model.joblib"
            output = root / "segments.csv"
            frame = pd.DataFrame(
                {
                    "user_id": ["001", "001", "001", "001"],
                    "trajectory_id": ["a", "a", "a", "a"],
                    "window_start": [
                        "2021-01-01 00:00:00",
                        "2021-01-01 00:01:00",
                        "2021-01-01 00:02:00",
                        "2021-01-01 00:03:00",
                    ],
                    "split": ["test"] * 4,
                    "canonical_mode": ["walk"] * 4,
                    "distance_m": [1.0, 1.0, 2.0, 2.0],
                }
            )
            frame.to_csv(dataset, index=False, encoding="utf-8-sig")
            model = DummyClassifier(strategy="most_frequent").fit([[1.0], [2.0]], ["walk", "walk"])
            joblib.dump({"model": model, "feature_columns": ["distance_m"], "classes": ["walk"]}, model_path)

            result = reconstruct_segments(dataset, model_path, output)

            segments = pd.read_csv(output, encoding="utf-8-sig")

        self.assertEqual(result["trajectory_count"], 1)
        self.assertEqual(result["segment_count"], 1)
        self.assertEqual(segments["window_count"].tolist(), [4])


if __name__ == "__main__":
    unittest.main()
