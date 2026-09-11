from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.common.encoding import detect_encoding


class EncodingDetectionTests(unittest.TestCase):
    def test_detects_utf8_and_bom(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = root / "plain.csv"
            plain.write_text("서울,rail\n", encoding="utf-8")
            bom = root / "bom.csv"
            bom.write_bytes("서울,rail\n".encode("utf-8-sig"))

            self.assertEqual(detect_encoding(plain), "utf-8")
            self.assertEqual(detect_encoding(bom), "utf-8-sig")

    def test_detects_cp949(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ktdb.csv"
            path.write_bytes("서울특별시,버스\n".encode("cp949"))

            self.assertEqual(detect_encoding(path), "cp949")

    def test_rejects_non_positive_sample_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_bytes(b"sample")

            with self.assertRaises(ValueError):
                detect_encoding(path, sample_size=0)


if __name__ == "__main__":
    unittest.main()

