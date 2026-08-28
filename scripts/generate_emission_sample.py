"""Generate documented emission-factor resolution examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.emission_factors.calculator import calculate_multimodal_trip, calculate_segment_emission
from src.emission_factors.parser import parse_workbook
from src.emission_factors.resolver import FactorResolver


def generate_sample(workbook: str | Path) -> dict[str, object]:
    resolver = FactorResolver(parse_workbook(workbook))
    cases = [
        ("walk", 2.0, {}),
        ("bike", 5.0, {}),
        ("car", 10.0, {"fuel_type": "petrol", "vehicle_size": "medium"}),
        ("car", 10.0, {"fuel_type": "unknown", "vehicle_size": "unknown"}),
        ("bus", 10.0, {"subtype": "local_bus"}),
        ("rail", 10.0, {"subtype": "underground"}),
        ("rail", 10.0, {}),
    ]
    outputs = []
    for mode, distance, kwargs in cases:
        factor = resolver.resolve_emission_factor(mode, **kwargs)
        outputs.append({"mode": mode, "distance_km": distance, "resolved_factor": factor, "co2e_g": calculate_segment_emission(distance, factor)})
    multimodal = calculate_multimodal_trip([
        {"mode": "walk", "distance_km": 0.8, "resolved_factor": resolver.resolve_emission_factor("walk")},
        {"mode": "rail", "distance_km": 10.9, "resolved_factor": resolver.resolve_emission_factor("rail", subtype="underground")},
        {"mode": "walk", "distance_km": 0.7, "resolved_factor": resolver.resolve_emission_factor("walk")},
    ])
    return {"source_workbook": str(workbook), "cases": outputs, "multimodal_trip": multimodal}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = generate_sample(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
