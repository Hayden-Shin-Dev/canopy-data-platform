"""KTDB 원본에서 Population Baseline 학습용 CSV를 재생성한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from src.common.logging_utils import configure_logging, get_logger
from src.config import (
    KTDB_RAW_DIR,
    KTDB_RAW_FILES,
    PROCESSED_DIR,
    RANDOM_SEED,
)
from src.ktdb.admin_area import load_admin_lookup
from src.ktdb.codebook import load_codebook
from src.ktdb.loader import iter_trip_chunks, load_person_table
from src.ktdb.modes import build_mode_mapping
from src.ktdb.purpose import filter_commute
from src.ktdb.split import assign_group_split
from src.ktdb.transform import build_feature_frame
from src.ktdb.schema import MODEL_FEATURES


OUTPUT_DIR = PROCESSED_DIR / "population_baseline" / "ktdb"
ALL_OUTPUT = OUTPUT_DIR / "01_population_model_training_all.csv"
COMMUTE_OUTPUT = OUTPUT_DIR / "02_population_model_training_commute.csv"
MAPPING_OUTPUT = OUTPUT_DIR / "05_mode_mapping.csv"
OUTPUT_COLUMNS = (
    "trip_id",
    "person_group_id",
    "actual_mode_sequence",
    "main_mode_raw_code",
    "survey_date",
    *MODEL_FEATURES,
    "actual_mode",
    "split",
)


def _prepare_output(frame: pd.DataFrame) -> pd.DataFrame:
    """출력 계약에 맞추고 아직 만들 수 없는 거리 값은 결측으로 둔다."""

    result = frame.copy()
    if "od_straight_distance_km" not in result:
        result["od_straight_distance_km"] = pd.NA
    if "distance_band" not in result:
        result["distance_band"] = pd.NA
    result["split"] = assign_group_split(result)
    for column in OUTPUT_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[list(OUTPUT_COLUMNS)]


def _append_csv(frame: pd.DataFrame, path: Path, first_write: bool) -> None:
    if frame.empty:
        return
    frame.to_csv(
        path,
        mode="w" if first_write else "a",
        header=first_write,
        index=False,
        encoding="utf-8-sig",
    )


def build_population_dataset(
    *,
    raw_dir: Path = KTDB_RAW_DIR,
    output_dir: Path = OUTPUT_DIR,
    chunksize: int = 50_000,
) -> dict[str, object]:
    """전체 원본을 순회해 all/commute 학습 CSV를 만든다."""

    if chunksize <= 0:
        raise ValueError("chunksize는 양수여야 함")
    logger = get_logger(__name__)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_path = output_dir / ALL_OUTPUT.name
    commute_path = output_dir / COMMUTE_OUTPUT.name
    mapping_path = output_dir / MAPPING_OUTPUT.name
    for path in (all_path, commute_path):
        if path.exists():
            path.unlink()

    person_path = raw_dir / KTDB_RAW_FILES["person"]
    trip_path = raw_dir / KTDB_RAW_FILES["trip"]
    codebook = load_codebook(raw_dir / KTDB_RAW_FILES["codebook"])
    admin_lookup = load_admin_lookup(raw_dir / KTDB_RAW_FILES["admin_area"])
    persons = load_person_table(person_path)
    build_mode_mapping(codebook).to_csv(mapping_path, index=False, encoding="utf-8-sig")

    raw_rows = 0
    valid_rows = 0
    commute_rows = 0
    excluded_rows = 0
    class_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    first_all = True
    first_commute = True
    for number, chunk in enumerate(iter_trip_chunks(trip_path, chunksize=chunksize), start=1):
        raw_rows += len(chunk)
        features = build_feature_frame(chunk, persons, codebook, admin_lookup)
        excluded_rows += len(chunk) - len(features)
        if features.empty:
            continue
        prepared = _prepare_output(features)
        commute = filter_commute(prepared)
        _append_csv(prepared, all_path, first_all)
        _append_csv(commute, commute_path, first_commute)
        first_all = first_all and prepared.empty
        first_commute = first_commute and commute.empty
        valid_rows += len(prepared)
        commute_rows += len(commute)
        class_counts.update(prepared["actual_mode"].astype(str))
        split_counts.update(prepared["split"].astype(str))
        logger.info("chunk=%s raw=%s valid=%s", number, len(chunk), len(prepared))

    summary = {
        "raw_rows": raw_rows,
        "valid_rows": valid_rows,
        "commute_rows": commute_rows,
        "excluded_rows": excluded_rows,
        "class_distribution": dict(class_counts),
        "split_distribution": dict(split_counts),
        "random_seed": RANDOM_SEED,
        "distance_status": "blocked: no coordinate source in current raw files",
        "outputs": [str(all_path), str(commute_path), str(mapping_path)],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=KTDB_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--chunksize", type=int, default=50_000)
    args = parser.parse_args()
    configure_logging()
    summary = build_population_dataset(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        chunksize=args.chunksize,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

