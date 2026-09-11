from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.common.file_inventory import discover_files, missing_files


class FileInventoryTests(unittest.TestCase):
    def test_inventory_reports_size_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            (raw_dir / "present.csv").write_bytes(b"abc")

            records = discover_files(raw_dir, ["present.csv", "missing.xlsx"])

            self.assertEqual(records[0].size_bytes, 3)
            self.assertTrue(records[0].exists)
            self.assertFalse(records[1].exists)
            self.assertEqual(missing_files(records), ["missing.xlsx"])


if __name__ == "__main__":
    unittest.main()

