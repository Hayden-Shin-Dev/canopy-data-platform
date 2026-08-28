import pandas as pd
import pytest

from src.emission_factors.calculator import calculate_multimodal_trip, calculate_segment_emission
from src.emission_factors.parser import OUTPUT_COLUMNS
from src.emission_factors.resolver import FactorResolver


def _row(mode, subtype, fuel, size, value, unit="gCO2e/vehicle.km"):
    return dict(zip(OUTPUT_COLUMNS, [mode, subtype, fuel, size, value, unit, value / 1000, "kg CO2e/km", "source", None, 2026, "test", "operational", False, f"{mode}-{subtype}-{fuel}-{size}"], strict=True))


def test_resolver_exact_and_documented_fallbacks() -> None:
    factors = pd.DataFrame([
        _row("car", "petrol_medium", "petrol", "medium", 174.11),
        _row("car", "unknown_average", "unknown", "average", 165.91),
        _row("bus", "average_local_bus", None, None, 101.51, "gCO2e/passenger.km"),
        _row("rail", "national_rail", None, None, 30.92, "gCO2e/passenger.km"),
        _row("walk", "conventional_walk", None, None, 0.0, "gCO2e/person.km"),
    ])
    resolver = FactorResolver(factors)
    exact = resolver.resolve_emission_factor("car", fuel_type="petrol", vehicle_size="medium")
    fallback = resolver.resolve_emission_factor("car", fuel_type="cng", vehicle_size="large")
    bus = resolver.resolve_emission_factor("bus", subtype="unknown")
    rail = resolver.resolve_emission_factor("rail", subtype="unknown")
    assert exact["fallback_used"] is False
    assert fallback["fallback_used"] is True
    assert fallback["resolved_subtype"] == "unknown_average"
    assert bus["fallback_used"] is True
    assert rail["resolved_subtype"] == "national_rail"


def test_calculator_rejects_bad_units_and_sums_segments() -> None:
    factor = {"factor_value": 100.0, "unit": "gCO2e/passenger.km", "canonical_mode": "bus", "resolved_subtype": "coach", "fallback_used": False}
    assert calculate_segment_emission(10.0, factor) == pytest.approx(1000.0)
    total = calculate_multimodal_trip([
        {"mode": "walk", "distance_km": 2.0, "resolved_factor": {"factor_value": 0.0, "unit": "gCO2e/person.km", "resolved_subtype": "conventional_walk", "fallback_used": False}},
        {"mode": "bus", "distance_km": 10.0, "resolved_factor": factor},
    ])
    assert total["trip_total_co2e_g"] == pytest.approx(1000.0)
    with pytest.raises(ValueError):
        calculate_segment_emission(1.0, {"factor_value": 1.0, "unit": "kgCO2e/km"})
