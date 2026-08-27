"""Create a reproducible manifest for immutable raw files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .file_inventory import REQUIRED_KTDB_FILES, discover_files, missing_files


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA256 digest of ``path`` using bounded memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_manifest(
    raw_dir: Path,
    *,
    source: str = "ktdb",
    root: Path | None = None,
    download_date: str | None = None,
) -> dict[str, Any]:
    """Hash every required raw file and return a JSON-serializable manifest.

    ``download_date`` is intentionally optional: the pipeline must not infer a
    download date from filesystem timestamps. The observed mtime is included
    only as a local diagnostic.
    """

    raw_dir = Path(raw_dir)
    records = discover_files(raw_dir, REQUIRED_KTDB_FILES)
    missing = missing_files(records)
    if missing:
        raise FileNotFoundError(", ".join(missing))

    files: list[dict[str, Any]] = []
    for record in records:
        path = Path(record.path)
        stat = path.stat()
        files.append(
            {
                "name": record.name,
                "path": _relative_path(path, root),
                "size_bytes": record.size_bytes,
                "sha256": sha256_file(path),
                "observed_mtime_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )

    return {
        "source": source,
        "download_date": download_date,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/ktdb"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/ktdb/raw_manifest.json"),
    )
    parser.add_argument("--download-date", default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path.cwd()
    manifest = build_manifest(
        args.raw_dir,
        root=root,
        download_date=args.download_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
