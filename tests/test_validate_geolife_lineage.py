import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from scripts.validate_geolife_lineage import validate_lineage


def test_lineage_connects_raw_labels_and_processed_windows() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        archive_path = root / "geolife.zip"
        headers = "header\n" * 6
        points = headers + "39.0,116.0,0,10,0,2021-01-01,00:00:00\n39.0,116.001,0,10,0,2021-01-01,00:00:10\n"
        labels = "Start Time\tEnd Time\tTransportation Mode\n" + "\n".join(
            f"2021/01/01 00:00:00\t2021/01/01 00:01:00\t{mode}" for mode in ["walk", "bike", "car", "bus", "subway"]
        ) + "\n"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("Geolife Trajectories 1.3/Data/001/Trajectory/1.plt", points)
            archive.writestr("Geolife Trajectories 1.3/Data/001/labels.txt", labels)
        processed = root / "windows.csv"
        pd.DataFrame(
            {
                "user_id": ["001"],
                "trajectory_id": ["1"],
                "window_start": ["2021-01-01 00:00:00"],
                "window_end": ["2021-01-01 00:01:00"],
                "canonical_mode": ["walk"],
                "split": ["test"],
            }
        ).to_csv(processed, index=False, encoding="utf-8-sig")

        result = validate_lineage(archive_path, processed)

    assert result["passed"] is True
    assert result["raw"]["point_count"] == 2
    assert result["processed"]["window_count"] == 1
    assert result["lineage"]["processed_trajectories_matching_raw"] == 1
