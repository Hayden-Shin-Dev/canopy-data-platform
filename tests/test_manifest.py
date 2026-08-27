from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from src.common.manifest import build_manifest, sha256_file


class ManifestTests(unittest.TestCase):
    def test_sha256_and_manifest_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "ktdb"
            raw_dir.mkdir()
            names = (
                "①개인특성.csv",
                "②이동특성.csv",
                "Code book.xlsx",
                "행정동코드_20210726(말소코드포함).xlsx",
            )
            for name in names:
                (raw_dir / name).write_bytes(name.encode("utf-8"))

            manifest = build_manifest(
                raw_dir,
                root=Path(directory),
                download_date=None,
            )

            expected = hashlib.sha256(names[0].encode("utf-8")).hexdigest()
            self.assertEqual(sha256_file(raw_dir / names[0]), expected)
            self.assertIsNone(manifest["download_date"])
            self.assertEqual(manifest["files"][0]["path"], "ktdb/①개인특성.csv")
            self.assertEqual(manifest["files"][0]["sha256"], expected)


if __name__ == "__main__":
    unittest.main()

