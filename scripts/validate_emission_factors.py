"""Validate normalized emission factors and their source-row lineage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.emission_factors.parser import OUTPUT_COLUMNS


def validate_reference(reference_csv: str | Path, source_workbook: str | Path | None = None) -> dict[str, object]:
    frame = pd.read_csv(reference_csv, encoding="utf-8-sig")
    missing = sorted(set(OUTPUT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"reference columns missing: {missing}")
    key = ["canonical_mode", "emission_subtype", "fuel_type", "vehicle_size"]
    duplicate_keys = int(frame.duplicated(key).sum())
    invalid_modes = sorted(set(frame["canonical_mode"]) - {"walk", "bike", "car", "bus", "rail"})
    invalid_units = sorted(set(frame["normalized_unit"]) - {"gCO2e/vehicle.km", "gCO2e/passenger.km", "gCO2e/person.km"})
    negative_factors = int((pd.to_numeric(frame["factor_value"], errors="coerce") < 0).sum())
    policy_rows = frame[frame["source_name"].eq("Canopy POC policy")]
    source_ids = set(frame.loc[~frame["source_row_identifier"].astype(str).str.startswith("canopy-policy-"), "source_row_identifier"].astype(str))
    source_missing: list[str] = []
    if source_workbook and source_ids:
        source = pd.read_excel(source_workbook, sheet_name="Factors by Category", header=5)
        source_missing = sorted(source_ids - set(source["ID"].dropna().astype(str)))
    result = {
        "reference_csv": str(reference_csv),
        "row_count": len(frame),
        "mode_counts": {str(k): int(v) for k, v in frame["canonical_mode"].value_counts().items()},
        "duplicate_key_count": duplicate_keys,
        "invalid_modes": invalid_modes,
        "invalid_units": invalid_units,
        "negative_factor_count": negative_factors,
        "policy_zero_rows": int((policy_rows["factor_value"] == 0).sum()),
        "source_row_count": len(source_ids),
        "source_rows_missing_from_workbook": source_missing,
    }
    result["passed"] = not any((duplicate_keys, invalid_modes, invalid_units, negative_factors, source_missing))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_csv", type=Path)
    parser.add_argument("--source-workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_reference(args.reference_csv, args.source_workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
