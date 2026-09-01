from pathlib import Path

import pytest

from src.aihub.filenames import label_filename, parse_tmc_filename


def test_parses_tmc_segments_without_assigning_unverified_names() -> None:
    identifier = parse_tmc_filename(
        "TMC-GPS-00000020-63303497e3053e15626f3e0f-26656271806545969e7bd272e2da26433-Dataset.csv"
    )
    assert identifier.uid == "00000020"
    assert identifier.part_a.startswith("6330")
    assert identifier.part_b.startswith("2665")


def test_builds_exact_label_filename() -> None:
    assert label_filename(Path("TMC-GPS-1-a-b-Dataset.csv")) == "TMC-LABEL-1-a-b-Label.csv"


def test_rejects_non_tmc_filename() -> None:
    with pytest.raises(ValueError):
        parse_tmc_filename("not-a-tmc.csv")
