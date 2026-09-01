from pathlib import Path
import json

import pytest

from src.aihub.replay import ReplaySelectionError, iter_aihub_payloads, select_test_trajectories, validate_replay_uid


def test_train_and_unknown_uids_are_rejected() -> None:
    manifest = {"00000001": "train", "00000007": "test"}
    with pytest.raises(ReplaySelectionError, match="REPLAY_REJECTED_TRAIN_UID"):
        validate_replay_uid("1", manifest)
    with pytest.raises(ReplaySelectionError, match="UNKNOWN_UID"):
        validate_replay_uid("999", manifest)
    assert validate_replay_uid("7", manifest) == "00000007"


def test_selects_five_modes_deterministically(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    manifest = {"groups": [{"user_id": f"{index:08d}", "split": "test"} for index in range(1, 6)]}
    (tmp_path / "split.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows = ["user_id,trajectory_id,source_class,canonical_mode,window_start,window_end,point_count,observed_duration_sec,invalid_coordinate_count,missing_coordinate_count,split"]
    for index, mode in enumerate(("walk", "bike", "car", "bus", "rail"), start=1):
        for part in range(3):
            trajectory = f"TMC-GPS-{index:08d}-abc-{part}-Dataset"
            start = part * 60
            minute = part
            rows.append(f"{index},{trajectory},X,{mode},2022-01-01 00:{minute:02d}:00,2022-01-01 00:{minute:02d}:59,60,59,0,0,test")
            gps = "timestamp,latitude,longitude,accuracy,altitude\n" + "\n".join(
                f"{1640995200000 + (start + second) * 1000},37.5,126.9,5,10" for second in range(60)
            )
            (source / f"{trajectory}.csv").write_text(gps, encoding="utf-8")
    windows = tmp_path / "windows.csv"
    windows.write_text("\n".join(rows), encoding="utf-8")
    output = tmp_path / "replay.json"
    result = select_test_trajectories(windows, tmp_path / "split.json", source, output, per_class=1)
    assert result["trajectory_count"] == 5
    assert result["class_counts"] == {mode: 1 for mode in ("walk", "bike", "car", "bus", "rail")}
    assert output.is_file()


def test_aihub_payload_has_no_ground_truth_fields(tmp_path: Path) -> None:
    path = tmp_path / "gps.csv"
    path.write_text(
        "timestamp,latitude,longitude,accuracy,altitude\n1700000000000,37.5,126.9,5.5,10.0\n",
        encoding="utf-8",
    )
    payload = next(iter_aihub_payloads({"uid": "00000007", "trajectory_id": "T", "gps_file": path.name}, source_root=tmp_path))
    assert payload["source"] == "aihub_real_gps"
    assert "ground_truth" not in payload
    assert payload["timestamp"].endswith("Z")
    assert payload["horizontal_accuracy_m"] == 5.5
    assert payload["altitude_m"] == 10.0
