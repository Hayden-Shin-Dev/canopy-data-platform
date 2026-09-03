from pathlib import Path

from scripts.run_aihub_official_smoke import _input_status


def test_input_status_marks_gps_only_release_incompatible(tmp_path: Path):
    gps_dir = tmp_path / "Validation" / "원천데이터" / "TS_교통수단판별_3.GPS_01.WALK"
    gps_dir.mkdir(parents=True)
    (gps_dir / "sample.csv").write_text("timestamp,latitude,longitude\n", encoding="utf-8")

    result = _input_status(tmp_path)

    assert result["present_modalities"] == ["gps"]
    assert set(result["missing_modalities"]) == {"imu", "ap", "bts"}
    assert result["format_compatible"] is False
    assert result["full_modality_available"] is False


def test_input_status_requires_official_sensor_tree(tmp_path: Path):
    for name in ("1.AP", "2.BTS", "3.GPS", "4.IMU"):
        (tmp_path / "origin" / name).mkdir(parents=True)

    result = _input_status(tmp_path)

    assert result["full_modality_available"] is True
    assert result["format_compatible"] is True
    assert result["missing_modalities"] == []
