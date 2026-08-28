"""Calculate operational CO2e from resolved factors without implicit unit conversion."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


SUPPORTED_UNITS = {"gCO2e/vehicle.km", "gCO2e/passenger.km", "gCO2e/person.km"}


def calculate_segment_emission(distance_km: float, resolved_factor: Mapping[str, object]) -> float:
    if distance_km < 0:
        raise ValueError("distance_km must be non-negative")
    unit = str(resolved_factor.get("unit", ""))
    if unit not in SUPPORTED_UNITS:
        raise ValueError(f"unsupported factor unit: {unit!r}")
    factor = float(resolved_factor["factor_value"])
    if factor < 0:
        raise ValueError("factor_value must be non-negative")
    return distance_km * factor


def calculate_multimodal_trip(segments: Iterable[Mapping[str, object]]) -> dict[str, object]:
    output_segments: list[dict[str, object]] = []
    total = 0.0
    for segment in segments:
        distance = float(segment["distance_km"])
        emission = calculate_segment_emission(distance, segment["resolved_factor"])
        factor = segment["resolved_factor"]
        item = {
            "mode": segment.get("mode", factor.get("canonical_mode")),
            "subtype": factor.get("resolved_subtype"),
            "distance_km": distance,
            "factor": factor["factor_value"],
            "unit": factor["unit"],
            "co2e_g": emission,
            "fallback_used": bool(factor.get("fallback_used", False)),
        }
        output_segments.append(item)
        total += emission
    return {"trip_total_co2e_g": total, "segments": output_segments}
