from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.ktdb.loader import iter_trip_chunks, load_person_table
from src.ktdb.schema import trip_columns


class LoaderTests(unittest.TestCase):
    def test_person_loader_keeps_identifiers_as_strings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "person.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["idx", "DATE"])
                writer.writeheader()
                writer.writerow({"idx": "0012", "DATE": "1021"})

            frame = load_person_table(path)

            self.assertEqual(frame.loc[0, "idx"], "0012")
            self.assertEqual(frame["idx"].dtype.name, "string")

    def test_trip_loader_yields_requested_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trip.csv"
            row = {column: "" for column in trip_columns()}
            row.update({"idx": "0012", "fid": "9", "TP5_1": "1"})
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(trip_columns()))
                writer.writeheader()
                writer.writerows([row, row])

            chunks = list(iter_trip_chunks(path, chunksize=1))

            self.assertEqual([len(chunk) for chunk in chunks], [1, 1])
            self.assertEqual(chunks[0].loc[0, "TP5_1"], "1")


if __name__ == "__main__":
    unittest.main()

