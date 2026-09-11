from pathlib import Path

import joblib
import pandas as pd

from scripts.validate_aihub_release import validate
from src.aihub.features import AIHUB_FEATURE_COLUMNS
from src.aihub.training import train_model


def test_validate_aihub_release_checks_hashes_and_user_overlap(tmp_path: Path) -> None:
    rows = []
    for split, users in (("train", range(10)), ("validation", range(10, 15)), ("test", range(15, 20))):
        for user in users:
            for index, mode in enumerate(("walk", "bike", "car", "bus", "rail")):
                row = {"user_id": f"u{user}", "canonical_mode": mode, "split": split}
                row.update({column: float(index) for column in AIHUB_FEATURE_COLUMNS})
                rows.append(row)
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame(rows).to_csv(dataset, index=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    artifact = tmp_path / "model.joblib"
    train_model(dataset, artifact, tmp_path / "metrics.json", model_type="extra_trees", n_estimators=2, split_manifest_path=manifest)
    result = validate(dataset, manifest, artifact)
    assert result["status"] == "PASS"
    assert all(value == 0 for value in result["user_overlap"].values())
