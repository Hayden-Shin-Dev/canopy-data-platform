import pandas as pd
import pytest

from src.emission_factors.parser import OUTPUT_COLUMNS
from src.emission_factors.resolver import FactorResolver
from src.integration.emissions import calculate_actual_emission, calculate_expected_emission


def _row(mode, subtype, value, unit):
    values = [mode, subtype, None, None, value, unit, value / 1000, "kg CO2e/km", "source", None, 2026, "test", "operational", False, f"{mode}-{subtype}"]
    return dict(zip(OUTPUT_COLUMNS, values, strict=True))


def _resolver():
    return FactorResolver(pd.DataFrame([
        _row("walk", "conventional_walk", 0.0, "gCO2e/person.km"),
        _row("bike", "conventional_bicycle", 0.0, "gCO2e/person.km"),
        _row("car", "unknown_average", 180.0, "gCO2e/vehicle.km"),
        _row("bus", "average_local_bus", 100.0, "gCO2e/passenger.km"),
        _row("rail", "national_rail", 40.0, "gCO2e/passenger.km"),
    ]))


def test_actual_emission_uses_final_mode_and_distance():
    result = calculate_actual_emission("car", 10.0, resolver=_resolver(), fuel_type="unknown", vehicle_size="average")

    assert result["co2e_g"] == pytest.approx(1800.0)
    assert result["resolved_factor"]["canonical_mode"] == "car"


def test_expected_emission_is_probability_weighted_and_reduction_keeps_negative():
    expected = calculate_expected_emission({"car": 0.5, "bus": 0.5}, 10.0, resolver=_resolver())
    actual = calculate_actual_emission("car", 10.0, resolver=_resolver(), fuel_type="unknown", vehicle_size="average")

    assert expected["expected_co2e_g"] == pytest.approx(1400.0)
    assert expected["expected_co2e_g"] - actual["co2e_g"] < 0
