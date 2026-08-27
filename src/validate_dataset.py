"""생성된 KTDB feature CSV가 schema와 데이터 계약을 지키는지 검사한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR, PROJECT_ROOT
from src.ktdb.schema import MODEL_FEATURES


DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "ktdb_population_features.schema.json"
DEFAULT_DATASET = PROCESSED_DIR / "population_baseline" / "ktdb" / "01_population_model_training_all.csv"
ALLOWED_MODES = {"walk", "bike", "car", "bus", "rail"}
ALLOWED_SPLITS = {"train", "validation", "test"}


def validate_feature_frame(frame: pd.DataFrame, schema_path: str | Path = DEFAULT_SCHEMA) -> dict[str, object]:
    """전체 frame의 필수 컬럼과 JSON schema 위반을 확인한다."""

    required = {
        "trip_id",
        "person_group_id",
        "actual_mode",
        "split",
        *MODEL_FEATURES,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"필수 feature 컬럼이 없습니다: {missing}")
    invalid_modes = sorted(set(frame["actual_mode"].dropna().astype(str)) - ALLOWED_MODES)
    if invalid_modes:
        raise ValueError(f"허용되지 않은 actual_mode가 있습니다: {invalid_modes}")
    invalid_splits = sorted(set(frame["split"].dropna().astype(str)) - ALLOWED_SPLITS)
    if invalid_splits:
        raise ValueError(f"허용되지 않은 split이 있습니다: {invalid_splits}")
    if frame["trip_id"].duplicated().any():
        raise ValueError("trip_id가 중복됩니다")

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for index, row in frame.iterrows():
        payload = row.where(row.notna(), None).to_dict()
        for error in validator.iter_errors(payload):
            errors.append(f"row={index}: {error.message}")
            if len(errors) >= 10:
                break
        if len(errors) >= 10:
            break
    if errors:
        raise ValueError("schema validation 실패: " + "; ".join(errors))
    return {"row_count": len(frame), "columns": len(frame.columns), "status": "valid"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    result = validate_feature_frame(
        pd.read_csv(args.dataset, encoding="utf-8-sig"), args.schema
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
