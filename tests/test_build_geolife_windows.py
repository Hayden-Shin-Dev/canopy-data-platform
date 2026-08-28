from __future__ import annotations

import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_geolife_windows import build_window_dataset


TRAJECTORY = """Geolife trajectory
WGS 84
Altitude is in Feet
Reserved 3
0,2,255,My Track,0,0,2,8421376
0
39.984702,116.318417,0,492,39744.1201851852,2008-10-23,02:53:04
39.984683,116.318450,0,493,39744.1202430556,2008-10-23,02:53:09
"""

LABELS = """Start Time\tEnd Time\tTransportation Mode
2008/10/23 02:53:04\t2008/10/23 02:54:04\tbus
"""


class GeoLifeWindowBuildTests(unittest.TestCase):
    def test_builds_csv_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "source.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "Geolife Trajectories 1.3/Data/000/Trajectory/sample.plt",
                    TRAJECTORY,
                )
                archive.writestr("Geolife Trajectories 1.3/Data/000/labels.txt", LABELS)
            output_path = root / "windows.csv"

            summary = build_window_dataset(archive_path, output_path, window_seconds=60)

            with output_path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            saved_summary = json.loads(output_path.with_suffix(".summary.json").read_text(encoding="utf-8"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["canonical_mode"], "bus")
        self.assertEqual(summary["selected_window_count"], 1)
        self.assertEqual(saved_summary["selected_mode_counts"], {"bus": 1})
        self.assertTrue(saved_summary["gps_quality"]["enabled"])
        self.assertEqual(saved_summary["gps_quality"]["stats"]["segment_break_count"], 0)

    def test_rejects_invalid_coverage(self) -> None:
        with self.assertRaises(ValueError):
            build_window_dataset("source.zip", "output.csv", min_label_coverage=0)


if __name__ == "__main__":
    unittest.main()
