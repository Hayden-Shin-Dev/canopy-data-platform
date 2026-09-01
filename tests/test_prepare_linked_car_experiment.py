from pathlib import Path

import pandas as pd

from scripts.prepare_linked_car_experiment import prepare
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    result = pd.DataFrame(rows)
    for column in AIHUB_FEATURE_COLUMNS:
        result[column] = 0.0
    return result


def test_prepare_adds_only_bounded_linked_train_rows(tmp_path: Path) -> None:
    columns = ["user_id", "trajectory_id", "source_class", "canonical_mode", "window_start", "window_end", "split", *AIHUB_FEATURE_COLUMNS]
    base = _frame([{"user_id": "u1", "trajectory_id": "t1", "source_class": "AI", "canonical_mode": "walk", "window_start": "a", "window_end": "b", "split": "train"}])[columns]
    linked = _frame([
        {"user_id": "car", "trajectory_id": f"t{i}", "source_class": "LINKED", "canonical_mode": "car", "window_start": str(i), "window_end": str(i), "split": "train"}
        for i in range(5)
    ] + [{"user_id": "other", "trajectory_id": "v1", "source_class": "LINKED", "canonical_mode": "car", "window_start": "0", "window_end": "0", "split": "validation"}])[columns]
    base_csv, linked_csv = tmp_path / "base.csv", tmp_path / "linked.csv"
    base.to_csv(base_csv, index=False)
    linked.to_csv(linked_csv, index=False)
    output, manifest = tmp_path / "out.csv", tmp_path / "manifest.json"
    result = prepare(base_csv, linked_csv, output, manifest, max_windows_per_user=2)
    frame = pd.read_csv(output)
    assert result["linked_rows"] == 2
    assert len(frame[frame["source_class"] == "LINKED"]) == 2
    assert set(frame[frame["source_class"] == "LINKED"]["split"]) == {"train"}
