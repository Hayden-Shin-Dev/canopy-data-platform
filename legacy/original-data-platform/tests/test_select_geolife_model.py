import json
import tempfile
import unittest
from pathlib import Path

from scripts.select_geolife_model import select_model


class SelectGeoLifeModelTests(unittest.TestCase):
    def test_selects_highest_validation_macro_f1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, score in (("weighted.json", 0.64), ("unweighted.json", 0.67)):
                path = Path(directory) / name
                path.write_text(
                    json.dumps(
                        {
                            "model": "RandomForestClassifier",
                            "metrics": {
                                "validation": {
                                    "accuracy": score,
                                    "macro_f1": score,
                                    "weighted_f1": score,
                                }
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)

            result = select_model(paths)

        self.assertEqual(result["selection_metric"], "validation_macro_f1")
        self.assertEqual(result["selected"]["metrics_path"], str(paths[1]))
        self.assertEqual(len(result["candidates"]), 2)

    def test_rejects_missing_validation_metric(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps({"metrics": {}}), encoding="utf-8")

            with self.assertRaises(ValueError):
                select_model([path])


if __name__ == "__main__":
    unittest.main()
