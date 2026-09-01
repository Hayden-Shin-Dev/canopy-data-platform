from pathlib import Path

import pandas as pd

from scripts.merge_aihub_windows import merge_tables
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def test_merges_training_and_validation_tables(tmp_path: Path) -> None:
    columns = {column: [1.0] for column in AIHUB_FEATURE_COLUMNS}
    train = pd.DataFrame({"user_id": ["u1"], "trajectory_id": ["t1"], "canonical_mode": ["walk"], **columns})
    valid = pd.DataFrame({"user_id": ["u2"], "trajectory_id": ["t2"], "canonical_mode": ["car"], **columns})
    train_path, valid_path, output = (tmp_path / name for name in ("train.csv", "valid.csv", "pool.csv"))
    train.to_csv(train_path, index=False)
    valid.to_csv(valid_path, index=False)
    summary = merge_tables(train_path, valid_path, output)
    assert summary["pool_rows"] == 2
    assert set(pd.read_csv(output)["user_id"]) == {"u1", "u2"}
