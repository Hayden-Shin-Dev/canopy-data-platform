from pathlib import Path

import pandas as pd

from scripts.compare_aihub_models import compare
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def test_compare_writes_metrics_table(tmp_path: Path, monkeypatch) -> None:
    rows = []
    for split, users in (("train", range(10)), ("validation", range(10, 15)), ("test", range(15, 20))):
        for user in users:
            for index, mode in enumerate(("walk", "bike", "car", "bus", "rail")):
                row = {"user_id": f"u{user}", "canonical_mode": mode, "split": split}
                row.update({column: float(index) for column in AIHUB_FEATURE_COLUMNS})
                rows.append(row)
    dataset = tmp_path / "dataset.csv"
    pd.DataFrame(rows).to_csv(dataset, index=False)
    monkeypatch.setattr("scripts.compare_aihub_models.DEFAULT_CANDIDATES", (("random_forest", "none"),))
    result = compare(dataset, tmp_path / "out", n_estimators=2)
    assert len(result) == 2
    assert (tmp_path / "out" / "comparison.csv").is_file()
