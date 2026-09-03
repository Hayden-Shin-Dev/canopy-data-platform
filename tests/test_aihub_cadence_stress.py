from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.aihub.cadence_stress import evaluate_cadence_stress


def test_cadence_stress_reports_flip_drift_and_coverage(tmp_path: Path) -> None:
    features = ["distance_m", "mean_speed_mps"]
    training = pd.DataFrame([[0.0, 0.0], [1.0, 1.0]], columns=features)
    model = RandomForestClassifier(n_estimators=2, random_state=1).fit(training, ["walk", "car"])
    model_path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "feature_columns": features, "classes": list(model.classes_)}, model_path)
    rows = []
    for index, mode in enumerate(("walk", "car")):
        for view, delta in (("native", 0.0), ("5s", 0.1)):
            rows.append(
                {
                    "user_id": f"u{index}",
                    "trajectory_id": f"window-{index}__{view}",
                    "canonical_mode": mode,
                    "split": "test",
                    "sampling_view": view,
                    "distance_m": float(index) + delta,
                    "mean_speed_mps": float(index) + delta,
                }
            )
    dataset = tmp_path / "cadence.csv"
    output = tmp_path / "report.json"
    pd.DataFrame(rows).to_csv(dataset, index=False)

    result = evaluate_cadence_stress(dataset, model_path, output)

    assert result["status"] == "PASS"
    assert result["views"]["5s"]["usable_window_coverage"] == 1
    assert result["views"]["5s"]["aligned_window_count"] == 2
    assert result["views"]["5s"]["mean_probability_total_variation_vs_native"] is not None
