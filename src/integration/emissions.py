"""Connect integration outputs to the existing Emission Factors resolver."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd

from src.emission_factors.calculator import calculate_segment_emission
from src.emission_factors.parser import OUTPUT_COLUMNS
from src.emission_factors.resolver import FactorResolver


DEFAULT_FACTORS_CSV = Path("data/processed/emission_factors/emission_factors_2026.csv")


def load_factor_resolver(factors_csv: str | Path = DEFAULT_FACTORS_CSV) -> FactorResolver:
    """Load the generated normalized factor table without re-parsing a workbook."""

    path = Path(factors_csv)
    if not path.is_file():
        raise FileNotFoundError(f"emission factor table not found: {path}")
    frame = pd.read_csv(path)
    missing = sorted(set(OUTPUT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"emission factor table columns missing: {missing}")
    return FactorResolver(frame)


def calculate_actual_emission(
    mode: str,
    distance_km: float,
    *,
    resolver: FactorResolver,
    subtype: str | None = None,
    fuel_type: str | None = None,
    vehicle_size: str | None = None,
) -> dict[str, object]:
    factor = resolver.resolve_emission_factor(mode, subtype=subtype, fuel_type=fuel_type, vehicle_size=vehicle_size)
    co2e_g = calculate_segment_emission(distance_km, factor)
    return {"mode": mode, "distance_km": distance_km, "co2e_g": co2e_g, "resolved_factor": factor}


def calculate_expected_emission(
    probabilities: Mapping[str, float],
    distance_km: float,
    *,
    resolver: FactorResolver,
) -> dict[str, object]:
    """Calculate expected CO2e as a probability-weighted sum of official factors."""

    values = {str(mode): max(0.0, float(value)) for mode, value in probabilities.items()}
    total_probability = sum(values.values())
    if total_probability <= 0:
        raise ValueError("expected mode probabilities must contain a positive total")
    values = {mode: value / total_probability for mode, value in values.items()}
    contributions: dict[str, dict[str, object]] = {}
    total = 0.0
    for mode, probability in values.items():
        # A population probability has no vehicle subtype; use the resolver's
        # documented unknown/average car fallback rather than inventing a factor.
        if mode == "car":
            factor = resolver.resolve_emission_factor(mode, fuel_type="unknown", vehicle_size="average")
        else:
            factor = resolver.resolve_emission_factor(mode)
        mode_emission = calculate_segment_emission(distance_km, factor)
        contributions[mode] = {"probability": probability, "factor": factor, "co2e_g": mode_emission}
        total += probability * mode_emission
    return {"distance_km": distance_km, "expected_co2e_g": total, "contributions": contributions}
