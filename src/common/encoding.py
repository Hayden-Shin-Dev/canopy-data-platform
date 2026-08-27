"""Encoding detection helpers for source files from external providers."""

from __future__ import annotations

from pathlib import Path


class EncodingDetectionError(ValueError):
    """Raised when a byte sample cannot be decoded by supported encodings."""


SUPPORTED_ENCODINGS: tuple[str, ...] = ("utf-8", "cp949", "euc-kr")
UTF8_BOM = b"\xef\xbb\xbf"


def detect_encoding(path: Path, sample_size: int = 1024 * 1024) -> str:
    """Detect a practical text encoding from the beginning of ``path``.

    UTF-8 with a BOM is identified first. For ordinary text, UTF-8 is tried
    before CP949 and EUC-KR; this keeps ASCII-only files consistently labelled
    as UTF-8 while correctly handling KTDB's Korean CP949 CSV files.
    """

    if sample_size <= 0:
        raise ValueError("sample_size must be positive")

    with Path(path).open("rb") as handle:
        sample = handle.read(sample_size)

    if sample.startswith(UTF8_BOM):
        return "utf-8-sig"

    for encoding in SUPPORTED_ENCODINGS:
        try:
            sample.decode(encoding)
        except UnicodeDecodeError:
            continue
        return encoding

    raise EncodingDetectionError(f"Unsupported text encoding: {path}")

