"""Audit large AI-Hub linked trajectory archives without extracting them."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import zipfile


def _sample_entry(archive: zipfile.ZipFile, entry: zipfile.ZipInfo, lines: int = 3) -> dict[str, object]:
    with archive.open(entry) as stream:
        text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.DictReader(text)
        rows = []
        for index, row in enumerate(reader):
            rows.append(dict(row))
            if index + 1 >= lines:
                break
        return {"name": entry.filename, "size_bytes": entry.file_size, "columns": list(reader.fieldnames or ()), "rows": rows}


def audit_archive(path: str | Path, *, sample_count: int = 5) -> dict[str, object]:
    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if not entries:
            raise ValueError(f"archive has no files: {archive_path}")
        samples = [_sample_entry(archive, entry) for entry in entries[:sample_count]]
        headers: dict[str, int] = {}
        for sample in samples:
            key = ",".join(sample["columns"])
            headers[key] = headers.get(key, 0) + 1
        return {
            "archive": str(archive_path),
            "archive_size_bytes": archive_path.stat().st_size,
            "entry_count": len(entries),
            "uncompressed_bytes": sum(entry.file_size for entry in entries),
            "sample_count": len(samples),
            "sample_headers": headers,
            "samples": samples,
            "contains_station_metadata": any(
                {"station_id", "station_latitude", "station_longitude", "station_line"} <= set(sample["columns"])
                for sample in samples
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--sample-count", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"archives": [audit_archive(path, sample_count=args.sample_count) for path in args.archives]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
