from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.summary import summarize_csv, summarize_frame, write_summary


def test_summarize_frame_reports_distribution_and_missing_rate() -> None:
    frame = pd.DataFrame(
        {
            "actual_mode": ["car", "walk", "car"],
            "split": ["train", "test", "train"],
            "commute_direction": ["to_work", "non_commute", "to_work"],
            "weekday": ["월", None, "화"],
            "od_straight_distance_km": [None, None, None],
        }
    )

    summary = summarize_frame(frame)

    assert summary["row_count"] == 3
    assert summary["class_distribution"] == {"car": 2, "walk": 1}
    assert summary["split_distribution"] == {"train": 2, "test": 1}
    assert summary["missing_rate"]["weekday"] == pytest.approx(1 / 3)
    assert summary["missing_rate"]["od_straight_distance_km"] == 1.0


def test_summarize_csv_reads_chunks_and_writes_json(tmp_path) -> None:
    csv_path = tmp_path / "features.csv"
    json_path = tmp_path / "reports" / "summary.json"
    pd.DataFrame(
        {
            "actual_mode": ["bus", "rail"],
            "split": ["validation", "test"],
            "commute_direction": ["to_work", "work_to_home"],
            "weekday": ["월", "화"],
        }
    ).to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = summarize_csv(csv_path, chunksize=1)
    write_summary(summary, json_path)

    assert summary["row_count"] == 2
    assert summary["class_distribution"] == {"bus": 1, "rail": 1}
    assert json_path.exists()
    assert '"row_count": 2' in json_path.read_text(encoding="utf-8")
