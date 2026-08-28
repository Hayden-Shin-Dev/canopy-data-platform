"""Parse only the transport rows used by Canopy from the official workbook."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


DEFAULT_MAPPING = Path(__file__).with_name("mapping.json")
OUTPUT_COLUMNS = (
    "canonical_mode", "emission_subtype", "fuel_type", "vehicle_size", "factor_value",
    "normalized_unit", "source_factor_value", "source_unit", "source_category", "source_activity",
    "source_year", "source_name", "ghg_boundary", "is_fallback", "source_row_identifier",
)


def load_mapping(path: str | Path = DEFAULT_MAPPING) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_row(row: pd.Series, mapping: dict[str, object], *, mode: str, subtype: str, fuel: str | None, size: str | None) -> dict[str, object] | None:
    value = row["GHG Conversion Factor 2026"]
    if pd.isna(value):
        return None
    uom = str(row["UOM"])
    normalized_unit = "gCO2e/vehicle.km" if mode == "car" else "gCO2e/passenger.km"
    return {
        "canonical_mode": mode,
        "emission_subtype": subtype,
        "fuel_type": fuel,
        "vehicle_size": size,
        "factor_value": float(value) * 1000.0,
        "normalized_unit": normalized_unit,
        "source_factor_value": float(value),
        "source_unit": f"kg CO2e/{uom}",
        "source_category": " | ".join(str(row[column]) for column in ("Level 1", "Level 2", "Level 3") if pd.notna(row[column])),
        "source_activity": str(row["Column Text"]) if pd.notna(row["Column Text"]) else None,
        "source_year": int(mapping["source_year"]),
        "source_name": mapping["source_name"],
        "ghg_boundary": "operational",
        "is_fallback": False,
        "source_row_identifier": str(row["ID"]),
    }


def parse_workbook(workbook: str | Path, mapping_path: str | Path = DEFAULT_MAPPING) -> pd.DataFrame:
    mapping = load_mapping(mapping_path)
    frame = pd.read_excel(workbook, sheet_name=mapping["workbook_sheet"], header=int(mapping["source_header_row"]))
    rows: list[dict[str, object]] = []
    car = mapping["car"]
    car_rows = frame[
        frame["Level 1"].eq(car["level_1"])
        & frame["Level 2"].eq(car["level_2"])
        & frame["UOM"].eq(car["uom"])
        & frame["GHG/Unit"].eq(mapping["ghg_unit"])
    ]
    for _, row in car_rows.iterrows():
        fuel = car["fuel"].get(row.get("Column Text"))
        size = car["size"].get(row.get("Level 3"))
        if fuel is None or size is None:
            continue
        parsed = _source_row(row, mapping, mode="car", subtype=f"{fuel}_{size}", fuel=fuel, size=size)
        if parsed is not None:
            rows.append(parsed)
    for mode in ("bus", "rail"):
        section = mapping[mode]
        selected = frame[
            frame["Level 1"].eq(section["level_1"])
            & frame["Level 2"].eq(section["level_2"])
            & frame["UOM"].eq(section["uom"])
            & frame["GHG/Unit"].eq(mapping["ghg_unit"])
        ]
        for _, row in selected.iterrows():
            subtype = section["subtype"].get(row.get("Level 3"))
            if subtype is None:
                continue
            parsed = _source_row(row, mapping, mode=mode, subtype=subtype, fuel=None, size=None)
            if parsed is not None:
                rows.append(parsed)
    for mode, policy in mapping["policy_modes"].items():
        rows.append({
            "canonical_mode": mode,
            "emission_subtype": policy["subtype"],
            "fuel_type": None,
            "vehicle_size": None,
            "factor_value": float(policy["factor_value"]),
            "normalized_unit": policy["normalized_unit"],
            "source_factor_value": float(policy["factor_value"]),
            "source_unit": policy["normalized_unit"],
            "source_category": "Canopy POC policy",
            "source_activity": None,
            "source_year": int(mapping["source_year"]),
            "source_name": "Canopy POC policy",
            "ghg_boundary": "operational",
            "is_fallback": False,
            "source_row_identifier": f"canopy-policy-{mode}-zero",
        })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def write_reference_dataset(workbook: str | Path, output_csv: str | Path, mapping_path: str | Path = DEFAULT_MAPPING) -> pd.DataFrame:
    result = parse_workbook(workbook, mapping_path)
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False, encoding="utf-8-sig")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    args = parser.parse_args()
    print(write_reference_dataset(args.workbook, args.output_csv, args.mapping).to_json(orient="records", force_ascii=False, indent=2))
