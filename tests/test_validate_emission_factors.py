from pathlib import Path

import pandas as pd

from scripts.validate_emission_factors import validate_reference
from src.emission_factors.parser import OUTPUT_COLUMNS


def test_reference_validation_accepts_unique_supported_rows(tmp_path: Path) -> None:
    row = dict(zip(OUTPUT_COLUMNS, ["walk", "conventional_walk", None, None, 0.0, "gCO2e/person.km", 0.0, "gCO2e/person.km", "Canopy POC policy", None, 2026, "Canopy POC policy", "operational", False, "canopy-policy-walk-zero"], strict=True))
    path = tmp_path / "reference.csv"
    pd.DataFrame([row]).to_csv(path, index=False, encoding="utf-8-sig")
    result = validate_reference(path)
    assert result["passed"] is True
    assert result["duplicate_key_count"] == 0
