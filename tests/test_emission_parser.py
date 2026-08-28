import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.emission_factors.parser import parse_workbook


def test_parser_uses_real_transport_rows_and_policy_factors() -> None:
    with tempfile.TemporaryDirectory() as directory:
        workbook = Path(directory) / "factors.xlsx"
        rows = [
            {"ID": "car-1", "Scope": "Scope 1", "Level 1": "Passenger vehicles", "Level 2": "Cars (by size)", "Level 3": "Medium car", "Level 4": None, "Column Text": "Petrol", "UOM": "km", "GHG/Unit": "kg CO2e", "GHG Conversion Factor 2026": 0.17411},
            {"ID": "car-null", "Scope": "Scope 1", "Level 1": "Passenger vehicles", "Level 2": "Cars (by size)", "Level 3": "Small car", "Level 4": None, "Column Text": "CNG", "UOM": "km", "GHG/Unit": "kg CO2e", "GHG Conversion Factor 2026": None},
            {"ID": "bus-1", "Scope": "Scope 3", "Level 1": "Business travel- land", "Level 2": "Bus", "Level 3": "Average local bus", "Level 4": None, "Column Text": None, "UOM": "passenger.km", "GHG/Unit": "kg CO2e", "GHG Conversion Factor 2026": 0.10151},
            {"ID": "rail-1", "Scope": "Scope 3", "Level 1": "Business travel- land", "Level 2": "Rail", "Level 3": "London Underground", "Level 4": None, "Column Text": None, "UOM": "passenger.km", "GHG/Unit": "kg CO2e", "GHG Conversion Factor 2026": 0.01549},
        ]
        frame = pd.DataFrame(rows)
        with pd.ExcelWriter(workbook) as writer:
            pd.DataFrame([[]] * 5).to_excel(writer, sheet_name="Factors by Category", index=False, header=False)
            frame.to_excel(writer, sheet_name="Factors by Category", index=False, startrow=5)

        result = parse_workbook(workbook)

    assert set(result["canonical_mode"]) == {"walk", "bike", "car", "bus", "rail"}
    car = result[result["source_row_identifier"] == "car-1"].iloc[0]
    assert car["factor_value"] == pytest.approx(174.11)
    assert car["normalized_unit"] == "gCO2e/vehicle.km"
    assert result[result["canonical_mode"] == "bus"]["emission_subtype"].tolist() == ["average_local_bus"]
