from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from src.geolife.raw import (
    GeoLifeFormatError,
    iter_label_intervals,
    iter_trajectory_points,
)


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


class GeoLifeRawParserTests(unittest.TestCase):
    def _make_zip(self, root: Path) -> Path:
        path = root / "geolife.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "Geolife Trajectories 1.3/Data/000/Trajectory/20081023025304.plt",
                TRAJECTORY,
            )
            archive.writestr(
                "Geolife Trajectories 1.3/Data/000/labels.txt",
                LABELS,
            )
        return path

    def test_reads_trajectory_and_label_from_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = self._make_zip(Path(directory))
            point = next(iter_trajectory_points(archive))
            label = next(iter_label_intervals(archive))

        self.assertEqual(point.user_id, "000")
        self.assertEqual(point.trajectory_id, "20081023025304")
        self.assertEqual(point.latitude, 39.984702)
        self.assertEqual(point.altitude_ft, 492.0)
        self.assertEqual(point.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "2008-10-23 02:53:04")
        self.assertEqual(label.user_id, "000")
        self.assertEqual(label.mode_raw, "bus")

    def test_reads_trajectory_from_extracted_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory_path = root / "Data" / "000" / "Trajectory" / "sample.plt"
            trajectory_path.parent.mkdir(parents=True)
            trajectory_path.write_text(TRAJECTORY, encoding="utf-8")
            point = next(iter_trajectory_points(root))

        self.assertEqual(point.user_id, "000")
        self.assertEqual(point.trajectory_id, "sample")

    def test_rejects_invalid_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory_path = root / "Data" / "000" / "Trajectory" / "bad.plt"
            trajectory_path.parent.mkdir(parents=True)
            trajectory_path.write_text(
                TRAJECTORY.replace("39.984702", "95.984702"),
                encoding="utf-8",
            )
            with self.assertRaises(GeoLifeFormatError):
                next(iter_trajectory_points(root))

    def test_non_strict_mode_reports_and_skips_invalid_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory_path = root / "Data" / "000" / "Trajectory" / "bad.plt"
            trajectory_path.parent.mkdir(parents=True)
            trajectory_path.write_text(
                TRAJECTORY.replace("39.984702", "95.984702"),
                encoding="utf-8",
            )
            errors: list[str] = []
            points = list(iter_trajectory_points(root, strict=False, on_error=errors.append))

        self.assertEqual(len(points), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("좌표 범위를 벗어났습니다", str(errors[0]))


if __name__ == "__main__":
    unittest.main()
