from types import SimpleNamespace

import pandas as pd

from scripts.experiment_ktdb_candidates import _brier_score, _evaluate


def test_ktdb_candidate_metrics_include_calibration_scores() -> None:
    target = pd.Series(["walk", "car"], dtype="string")
    data = SimpleNamespace(features=pd.DataFrame({"x": [1, 2]}), target=target)

    class Model:
        classes_ = ["walk", "bike", "car", "bus", "rail"]

        def predict_proba(self, frame):
            return [[0.8, 0.05, 0.1, 0.03, 0.02], [0.1, 0.05, 0.7, 0.1, 0.05]][: len(frame)]

    result = _evaluate(Model(), data, split="test")
    assert result["split"] == "test"
    assert result["row_count"] == 2
    assert 0.0 <= result["multiclass_brier"] <= 2.0
    assert result["log_loss"] > 0
    assert _brier_score(target, [[1.0, 0, 0, 0, 0], [0, 0, 1.0, 0, 0]], list(Model.classes_)) == 0.0
