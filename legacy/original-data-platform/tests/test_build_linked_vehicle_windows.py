from pathlib import Path
import zipfile

import pandas as pd

from scripts.build_linked_vehicle_windows import build


def test_build_linked_vehicle_windows_labels_car_and_keeps_user_split(tmp_path: Path) -> None:
    archive_path = tmp_path / "vehicle.zip"
    rows = ["timestamp,latitude,longitude"]
    for index in range(121):
        rows.append(f"{1_700_000_000_000 + index * 1000},37.5,{126.9 + index * 0.00001}")
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("TX-0000000A-0000000A_1700000000-Dataset.csv", "\n".join(rows))
        archive.writestr("malformed.csv", "timestamp,lat\n1,2\n")
    output = tmp_path / "windows.csv"
    assert build([archive_path], output) >= 1
    frame = pd.read_csv(output)
    assert set(frame["canonical_mode"]) == {"car"}
    assert set(frame["source_class"]) == {"LINKED_VEHICLE"}
    assert frame["accuracy_missing_ratio"].iloc[0] == 1.0
    assert frame["altitude_missing_ratio"].iloc[0] == 1.0


def test_build_linked_vehicle_windows_skips_csv_error_entry(tmp_path: Path) -> None:
    archive_path = tmp_path / "oversized.zip"
    oversized = "timestamp,latitude,longitude\n" + ("1," + "x" * 140_000 + ",2\n")
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("broken.csv", oversized)
    output = tmp_path / "windows.csv"
    assert build([archive_path], output) == 0
