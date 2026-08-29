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
    KTDB_SGIS_MAPPING_PATH,
    KTDB_UNMATCHED_REPORT_PATH,
    PROCESSED_DIR,
    REFERENCE_DIR,
    RANDOM_SEED,
    SGIS_CENTROID_PATH,
    SGIS_RAW_RESPONSE_DIR,
)
from src.ktdb.admin_area import load_admin_lookup
from src.ktdb.admin_centroids import load_or_collect_centroids
from src.ktdb.admin_matching import (
    attach_admin_centroids,
    build_admin_centroid_mapping,
    build_unmatched_report,
    inspect_code_systems,
)
from src.ktdb.codebook import load_codebook
from src.ktdb.distance import add_distance_band, add_projected_od_distance
from src.ktdb.distance_report import summarize_distance_coverage
from src.ktdb.loader import iter_trip_chunks, load_person_table
from src.ktdb.sgis import SgisClient, load_sgis_credentials
from src.ktdb.lookup import build_population_lookup
from src.ktdb.modes import build_mode_mapping
from src.ktdb.purpose import filter_commute
from src.ktdb.split import assign_group_split
from src.ktdb.summary import summarize_csv, write_summary
from src.ktdb.transform import build_feature_frame
from src.ktdb.schema import MODEL_FEATURES


OUTPUT_DIR = PROCESSED_DIR / "population_baseline" / "ktdb"
ALL_OUTPUT = OUTPUT_DIR / "01_population_model_training_all.csv"
COMMUTE_OUTPUT = OUTPUT_DIR / "02_population_model_training_commute.csv"
MAPPING_OUTPUT = OUTPUT_DIR / "05_mode_mapping.csv"
ALL_LOOKUP_OUTPUT = OUTPUT_DIR / "03_population_lookup_all.csv"
COMMUTE_LOOKUP_OUTPUT = OUTPUT_DIR / "04_population_lookup_commute.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "06_dataset_summary.json"
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


def _load_sgis_reference(
    centroid_path: Path,
    *,
    refresh_sgis: bool,
    sgis_timeout_seconds: float,
    sgis_max_retries: int,
    sgis_request_interval_seconds: float,
) -> pd.DataFrame:
    client = None
    if refresh_sgis or not centroid_path.is_file():
        key, secret = load_sgis_credentials()
        client = SgisClient(
            key,
            secret,
            timeout_seconds=sgis_timeout_seconds,
            max_retries=sgis_max_retries,
            request_interval_seconds=sgis_request_interval_seconds,
        )
    return load_or_collect_centroids(
        centroid_path,
        client=client,
        raw_response_dir=SGIS_RAW_RESPONSE_DIR,
        refresh=refresh_sgis,
    )


def build_population_dataset(
    *,
    raw_dir: Path = KTDB_RAW_DIR,
    output_dir: Path = OUTPUT_DIR,
    chunksize: int = 50_000,
    lookup_min_samples: int = 30,
    centroid_path: Path = SGIS_CENTROID_PATH,
    refresh_sgis: bool = False,
    sgis_timeout_seconds: float = 20.0,
    sgis_max_retries: int = 3,
    sgis_request_interval_seconds: float = 0.2,
) -> dict[str, object]:
    """전체 원본을 순회해 all/commute 학습 CSV를 만든다."""

    if chunksize <= 0:
        raise ValueError("chunksize는 양수여야 함")
    if lookup_min_samples < 1:
        raise ValueError("lookup_min_samples는 1 이상이어야 합니다")
    logger = get_logger(__name__)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_path = output_dir / ALL_OUTPUT.name
    commute_path = output_dir / COMMUTE_OUTPUT.name
    mapping_path = output_dir / MAPPING_OUTPUT.name
    all_lookup_path = output_dir / ALL_LOOKUP_OUTPUT.name
    commute_lookup_path = output_dir / COMMUTE_LOOKUP_OUTPUT.name
    summary_path = output_dir / SUMMARY_OUTPUT.name
    for path in (all_path, commute_path, all_lookup_path, commute_lookup_path, summary_path):
        if path.exists():
            path.unlink()

    person_path = raw_dir / KTDB_RAW_FILES["person"]
    trip_path = raw_dir / KTDB_RAW_FILES["trip"]
    codebook = load_codebook(raw_dir / KTDB_RAW_FILES["codebook"])
    admin_lookup = load_admin_lookup(raw_dir / KTDB_RAW_FILES["admin_area"])
    persons = load_person_table(person_path)
    centroids = _load_sgis_reference(
        centroid_path,
        refresh_sgis=refresh_sgis,
        sgis_timeout_seconds=sgis_timeout_seconds,
        sgis_max_retries=sgis_max_retries,
        sgis_request_interval_seconds=sgis_request_interval_seconds,
    )
    code_system = inspect_code_systems(admin_lookup, centroids)
    mapping = build_admin_centroid_mapping(admin_lookup, centroids)
    KTDB_SGIS_MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(KTDB_SGIS_MAPPING_PATH, index=False, encoding="utf-8-sig")
    logger.info("SGIS centroid reference loaded: %s", centroid_path)
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
        if not features.empty:
            features = attach_admin_centroids(features, mapping)
            features = add_projected_od_distance(features)
            features = add_distance_band(features)
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

    all_frame = pd.DataFrame()
    unmatched_report = pd.DataFrame(
        columns=("side", "ktdb_admin_code", "ktdb_full_name", "match_status", "row_count")
    )
    distance_summary = summarize_distance_coverage(
        pd.DataFrame(
            columns=(
                "origin_x",
                "origin_y",
                "destination_x",
                "destination_y",
                "od_straight_distance_km",
                "distance_band",
            )
        ),
        sgis_admin_dong_count=len(centroids),
        unmatched=unmatched_report,
    )
    if valid_rows:
        all_frame = pd.read_csv(all_path, encoding="utf-8-sig")
        unmatched_report = build_unmatched_report(all_frame, mapping)
        KTDB_UNMATCHED_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        unmatched_report.to_csv(KTDB_UNMATCHED_REPORT_PATH, index=False, encoding="utf-8-sig")
        distance_summary = summarize_distance_coverage(
            all_frame,
            sgis_admin_dong_count=len(centroids),
            unmatched=unmatched_report,
        )
        build_population_lookup(all_frame, min_samples=lookup_min_samples).to_csv(
            all_lookup_path, index=False, encoding="utf-8-sig"
        )
        if commute_rows:
            commute_frame = pd.read_csv(commute_path, encoding="utf-8-sig")
            build_population_lookup(commute_frame, min_samples=lookup_min_samples).to_csv(
                commute_lookup_path, index=False, encoding="utf-8-sig"
            )
        else:
            pd.DataFrame().to_csv(commute_lookup_path, index=False, encoding="utf-8-sig")
    else:
        KTDB_UNMATCHED_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        unmatched_report.to_csv(KTDB_UNMATCHED_REPORT_PATH, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(all_lookup_path, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(commute_lookup_path, index=False, encoding="utf-8-sig")

    distance_summary["unmatched_admin_dongs"] = unmatched_report.to_dict(orient="records")

    summary = {
        "raw_rows": raw_rows,
        "valid_rows": valid_rows,
        "commute_rows": commute_rows,
        "excluded_rows": excluded_rows,
        "class_distribution": dict(class_counts),
        "split_distribution": dict(split_counts),
        "random_seed": RANDOM_SEED,
        "lookup_min_samples": lookup_min_samples,
        "centroid_path": str(centroid_path),
        "distance_status": "available: SGIS EPSG:5179 to WGS84 Haversine",
        "sgis": distance_summary,
        "code_system": code_system,
        "unmatched_report": str(KTDB_UNMATCHED_REPORT_PATH),
        "centroid_mapping": str(KTDB_SGIS_MAPPING_PATH),
        "outputs": [
            str(all_path),
            str(commute_path),
            str(all_lookup_path),
            str(commute_lookup_path),
            str(mapping_path),
            str(KTDB_SGIS_MAPPING_PATH),
            str(KTDB_UNMATCHED_REPORT_PATH),
        ],
    }
    summary["all_dataset"] = summarize_csv(all_path) if valid_rows else {"row_count": 0}
    summary["commute_dataset"] = summarize_csv(commute_path) if commute_rows else {"row_count": 0}
    summary["outputs"].append(str(summary_path))
    write_summary(summary, summary_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=KTDB_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--chunksize", type=int, default=50_000)
    parser.add_argument("--lookup-min-samples", type=int, default=30)
    parser.add_argument("--centroid-file", type=Path, default=SGIS_CENTROID_PATH)
    parser.add_argument(
        "--refresh-sgis",
        action="store_true",
        help="기존 centroid CSV가 있어도 SGIS 2021 reference를 다시 수집합니다.",
    )
    parser.add_argument("--sgis-timeout", type=float, default=20.0)
    parser.add_argument("--sgis-max-retries", type=int, default=3)
    parser.add_argument("--sgis-request-interval", type=float, default=0.2)
    args = parser.parse_args()
    configure_logging()
    summary = build_population_dataset(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        chunksize=args.chunksize,
        lookup_min_samples=args.lookup_min_samples,
        centroid_path=args.centroid_file,
        refresh_sgis=args.refresh_sgis,
        sgis_timeout_seconds=args.sgis_timeout,
        sgis_max_retries=args.sgis_max_retries,
        sgis_request_interval_seconds=args.sgis_request_interval,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
