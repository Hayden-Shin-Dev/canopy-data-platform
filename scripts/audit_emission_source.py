"""Audit the GOV.UK 2026 flat-format conversion-factor workbook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


HEADER_ROW = 5
REQUIRED_COLUMNS = (
    "ID", "Scope", "Level 1", "Level 2", "Level 3", "Level 4",
    "Column Text", "UOM", "GHG/Unit", "GHG Conversion Factor 2026",
)


def audit_workbook(path: str | Path) -> dict[str, object]:
    workbook = Path(path)
    excel = pd.ExcelFile(workbook)
    factors = pd.read_excel(workbook, sheet_name="Factors by Category", header=HEADER_ROW)
    missing = [column for column in REQUIRED_COLUMNS if column not in factors.columns]
    if missing:
        raise ValueError(f"required workbook columns missing: {missing}")
    factors = factors[factors["ID"].notna()].copy()

    def values(column: str) -> list[str]:
        return sorted(factors[column].dropna().astype(str).unique().tolist())

    passenger = factors[factors["Level 1"].eq("Passenger vehicles")]
    business_land = factors[factors["Level 1"].eq("Business travel- land")]
    bus = factors[factors["Level 2"].eq("Bus")]
    rail = factors[factors["Level 2"].eq("Rail")]
    car = factors[factors["Level 2"].isin(["Cars (by size)", "Cars (by market segment)"])]
    text = factors["Column Text"].fillna("").astype(str)
    result = {
        "source_file": str(workbook),
        "sheet_names": excel.sheet_names,
        "factor_sheet": {
            "header_row_zero_based": HEADER_ROW,
            "row_count": int(len(factors)),
            "column_count": int(len(factors.columns)),
            "columns": factors.columns.tolist(),
        },
        "units": values("UOM"),
        "ghg_units": values("GHG/Unit"),
        "scope_values": values("Scope"),
        "categories": {
            "passenger_vehicle_rows": int(len(passenger)),
            "business_land_rows": int(len(business_land)),
            "car_rows": int(len(car)),
            "bus_rows": int(len(bus)),
            "rail_rows": int(len(rail)),
            "level_1": values("Level 1"),
            "level_2": values("Level 2"),
        },
        "checks": {
            "wtt_rows": int(factors["Level 1"].astype(str).str.startswith("WTT-").sum()),
            "bev_rows": int(text.str.contains("Battery Electric Vehicle", regex=False).sum()),
            "vehicle_size_values": sorted(car["Level 3"].dropna().astype(str).unique().tolist()),
            "fuel_values": sorted(text[text.isin(["Petrol", "Diesel", "Hybrid", "Plug-in Hybrid Electric Vehicle", "Battery Electric Vehicle", "Unknown"])].unique().tolist()),
            "average_unknown_rows": int(text.isin(["Average", "Unknown"]).sum()),
            "null_factor_rows": int(factors["GHG Conversion Factor 2026"].isna().sum()),
        },
        "transport_categories": {
            "bus_level_3": sorted(bus["Level 3"].dropna().astype(str).unique().tolist()),
            "rail_level_3": sorted(rail["Level 3"].dropna().astype(str).unique().tolist()),
            "car_level_2": sorted(car["Level 2"].dropna().astype(str).unique().tolist()),
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_workbook(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
