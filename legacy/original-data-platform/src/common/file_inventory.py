"""Discover required raw files without changing or parsing their contents."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_KTDB_FILES: tuple[str, ...] = (
    "①개인특성.csv",
    "②이동특성.csv",
    "Code book.xlsx",
    "행정동코드_20210726(말소코드포함).xlsx",
)


@dataclass(frozen=True)
class FileRecord:
    """A filesystem-only description of one expected input file."""

    name: str
    path: str
    exists: bool
    size_bytes: int


def discover_files(
    raw_dir: Path,
    expected_files: Iterable[str] = REQUIRED_KTDB_FILES,
) -> list[FileRecord]:
    """Return records for expected files under ``raw_dir``.

    This function intentionally does not open, rename, or modify any file. A
    missing input is represented as ``exists=False`` so callers can present a
    complete diagnostic before deciding whether to stop.
    """

    raw_dir = Path(raw_dir)
    records: list[FileRecord] = []
    for filename in expected_files:
        path = raw_dir / filename
        exists = path.is_file()
        records.append(
            FileRecord(
                name=filename,
                path=str(path),
                exists=exists,
                size_bytes=path.stat().st_size if exists else 0,
            )
        )
    return records


def missing_files(records: Iterable[FileRecord]) -> list[str]:
    """Return missing filenames from an inventory."""

    return [record.name for record in records if not record.exists]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/ktdb"),
        help="Directory containing KTDB raw files (default: data/raw/ktdb)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    records = discover_files(args.raw_dir)
    payload = {
        "raw_dir": str(args.raw_dir),
        "files": [asdict(record) for record in records],
        "missing_files": missing_files(records),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not payload["missing_files"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

