from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.assign_geolife_splits import assign_splits


class GeoLifeSplitScriptTests(unittest.TestCase):
    def test_preserves_leading_zero_in_user_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            output_path = root / "output.csv"
            with input_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["user_id", "canonical_mode"])
                writer.writeheader()
                for user_id in ("010", "020", "030"):
                    writer.writerow({"user_id": user_id, "canonical_mode": "walk"})

            assign_splits(input_path, output_path)
            with output_path.open(encoding="utf-8-sig", newline="") as stream:
                user_ids = {row["user_id"] for row in csv.DictReader(stream)}

            self.assertEqual(user_ids, {"010", "020", "030"})

    def test_reuses_reference_split_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.csv"
            reference_path = root / "reference.csv"
            output_path = root / "output.csv"
            input_path.write_text(
                "user_id,canonical_mode\n010,walk\n020,bus\n010,walk\n",
                encoding="utf-8",
            )
            reference_path.write_text(
                "user_id,split\n010,validation\n020,test\n",
                encoding="utf-8",
            )

            assign_splits(input_path, output_path, reference_split_csv=reference_path)
            with output_path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual([row["split"] for row in rows], ["validation", "test", "validation"])


if __name__ == "__main__":
    unittest.main()
