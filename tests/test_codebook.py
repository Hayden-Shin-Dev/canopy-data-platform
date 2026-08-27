from __future__ import annotations

import unittest

from src.config import KTDB_RAW_DIR, KTDB_RAW_FILES
from src.ktdb.codebook import load_codebook, normalize_code


class CodebookTests(unittest.TestCase):
    def test_normalize_code_handles_excel_numbers_and_blanks(self) -> None:
        self.assertEqual(normalize_code(7.0), "7")
        self.assertEqual(normalize_code(" 07 "), "7")
        self.assertEqual(normalize_code(""), "")

    @unittest.skipUnless(
        (KTDB_RAW_DIR / KTDB_RAW_FILES["codebook"]).is_file(),
        "로컬 KTDB 원본이 있을 때만 실제 Code Book을 확인함",
    )
    def test_real_codebook_contains_required_values(self) -> None:
        codebook = load_codebook(KTDB_RAW_DIR / KTDB_RAW_FILES["codebook"])

        self.assertEqual(codebook.values_for("TP2")["3"], "출근")
        self.assertEqual(
            codebook.values_for("TP5_1")["7"],
            "지하철/전철/경전철",
        )
        self.assertIn("DATE", codebook.variable_labels)


if __name__ == "__main__":
    unittest.main()
