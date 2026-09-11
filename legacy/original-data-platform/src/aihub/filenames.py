"""AI-Hub TMC filename parsing without guessing identifier semantics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_TMC_PATTERN = re.compile(
    r"^TMC-GPS-(?P<uid>[^-]+)-(?P<part_a>[^-]+)-(?P<part_b>[^-]+)-Dataset\.csv$"
)


@dataclass(frozen=True)
class TmcIdentifier:
    """Identifier segments as written in the filename.

    ``part_a`` and ``part_b`` are intentionally neutral names until the
    official AI-Hub metadata confirms whether they are TID, SID, or another
    identifier.
    """

    uid: str
    part_a: str
    part_b: str


def parse_tmc_filename(path: str | Path) -> TmcIdentifier:
    match = _TMC_PATTERN.fullmatch(Path(path).name)
    if match is None:
        raise ValueError(f"AI-Hub TMC GPS filename format is not supported: {path}")
    return TmcIdentifier(
        uid=match.group("uid"),
        part_a=match.group("part_a"),
        part_b=match.group("part_b"),
    )


def label_filename(gps_path: str | Path) -> str:
    name = Path(gps_path).name
    parse_tmc_filename(name)
    return name.replace("TMC-GPS-", "TMC-LABEL-").replace("-Dataset.csv", "-Label.csv")
