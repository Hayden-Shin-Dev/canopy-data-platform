import json
from pathlib import Path

import joblib
import pandas as pd

from src.aihub.config import CANOPY_MODES
from src.aihub.features import AIHUB_FEATURE_COLUMNS
from src.aihub.selection import select_candidate


def test_candidate_selection_keeps_test_for_the_validation_winner(tmp_path: Path) -> None:
    rows = []
    groups = []
    for split_index, split in enumerate(("train", "validation", "test")):
        for mode_index, mode in enumerate(CANOPY_MODES):
            user = f"{split}-{mode}"
            groups.append({"user_id": user, "split": split})
            row = {column: float(mode_index + split_index / 10) for column in AIHUB_FEATURE_COLUMNS}
            row.update({"user_id": user, "trajectory_id": user, "canonical_mode": mode, "split": split})
            rows.append(row)
    canonical = pd.DataFrame(rows)
    cadence = pd.concat([canonical, canonical[canonical["split"] == "train"]], ignore_index=True)
    canonical_path = tmp_path / "canonical.csv"
    cadence_path = tmp_path / "cadence.csv"
    manifest_path = tmp_path / "manifest.json"
    model_path = tmp_path / "model.joblib"
    report_path = tmp_path / "report.json"
    canonical.to_csv(canonical_path, index=False)
    cadence.to_csv(cadence_path, index=False)
    manifest_path.write_text(json.dumps({"groups": groups}), encoding="utf-8")

    report = select_candidate(
        canonical_path,
        cadence_path,
        manifest_path,
        model_path,
        report_path,
        n_estimators=2,
    )

    assert report["status"] == "PASS"
    assert all("test" not in candidate for candidate in report["candidates"])
    assert report["selected_metrics"]["test"]["row_count"] == len(CANOPY_MODES)
    assert joblib.load(model_path)["feature_version"] == "aihub-canonical-raw120-v2"
