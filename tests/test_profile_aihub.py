import csv
from pathlib import Path

from scripts.profile_aihub import main


def test_profile_cli_writes_json(monkeypatch, tmp_path: Path, capsys) -> None:
    raw_base = tmp_path / "Training" / "01.raw"
    label_base = tmp_path / "Training" / "02.labels"
    for source_class in ("WALK", "BIKE", "CAR", "BUS", "SUBWAY"):
        (raw_base / f"TS_{source_class}").mkdir(parents=True)
        (label_base / f"TL_{source_class}").mkdir(parents=True)
    gps = raw_base / "TS_CAR" / "TMC-GPS-1-a-b-Dataset.csv"
    label = label_base / "TL_CAR" / "TMC-LABEL-1-a-b-Label.csv"
    with gps.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "accuracy", "latitude", "longitude", "altitude"])
        writer.writerow(["1000", "1", "37.5", "126.9", "0"])
        writer.writerow(["2000", "1", "37.5", "126.9", "0"])
    with label.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "label", "detail_label"])
        writer.writerow(["1000", "2", "5"])
        writer.writerow(["2000", "2", "5"])
    output = tmp_path / "profile.json"
    monkeypatch.setattr("sys.argv", ["profile_aihub", str(tmp_path), str(output)])
    main()
    assert output.is_file()
    assert '"trajectory_count": 1' in output.read_text(encoding="utf-8")
