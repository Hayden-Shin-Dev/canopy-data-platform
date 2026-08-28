"""Resolve Canopy mode/subtype requests against the normalized reference table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .parser import OUTPUT_COLUMNS, parse_workbook


class FactorResolver:
    def __init__(self, factors: pd.DataFrame):
        missing = sorted(set(OUTPUT_COLUMNS) - set(factors.columns))
        if missing:
            raise ValueError(f"factor table columns missing: {missing}")
        key = ["canonical_mode", "emission_subtype", "fuel_type", "vehicle_size"]
        if factors.duplicated(key).any():
            raise ValueError("duplicate canonical factor key")
        self._factors = factors.copy()
        self._key = key

    @classmethod
    def from_workbook(cls, workbook: str | Path, mapping_path: str | Path | None = None) -> "FactorResolver":
        return cls(parse_workbook(workbook, mapping_path) if mapping_path else parse_workbook(workbook))

    def _find(self, mode: str, subtype: str | None, fuel: str | None, size: str | None) -> pd.Series | None:
        query = self._factors[self._factors["canonical_mode"].eq(mode)]
        if subtype is not None:
            query = query[query["emission_subtype"].eq(subtype)]
        if fuel is not None:
            query = query[query["fuel_type"].eq(fuel)]
        if size is not None:
            query = query[query["vehicle_size"].eq(size)]
        return None if query.empty else query.iloc[0]

    def resolve_emission_factor(
        self,
        canonical_mode: str,
        subtype: str | None = None,
        fuel_type: str | None = None,
        vehicle_size: str | None = None,
    ) -> dict[str, object]:
        mode = canonical_mode.strip().lower()
        if mode not in {"walk", "bike", "car", "bus", "rail"}:
            raise ValueError(f"unsupported canonical mode: {canonical_mode!r}")
        attempts: list[tuple[str | None, str | None, str | None, str]] = []
        if mode in {"walk", "bike"}:
            attempts = [(subtype or f"conventional_{'walk' if mode == 'walk' else 'bicycle'}", None, None, "policy default")]
        elif mode == "car":
            attempts = [
                (f"{fuel_type}_{vehicle_size}" if fuel_type and vehicle_size else None, fuel_type, vehicle_size, "exact fuel and size"),
                (f"{fuel_type}_average" if fuel_type else None, fuel_type, "average", "exact fuel and average size"),
                (f"unknown_{vehicle_size}" if vehicle_size else None, "unknown", vehicle_size, "unknown fuel and requested size"),
                ("unknown_average", "unknown", "average", "official average/unknown fallback"),
            ]
        elif mode == "bus":
            attempts = [(subtype, None, None, "exact bus subtype"), ("average_local_bus", None, None, "average local bus fallback")]
        else:
            attempts = [(subtype, None, None, "exact rail subtype"), ("national_rail", None, None, "national rail fallback")]
        selected: pd.Series | None = None
        reason = ""
        for candidate_subtype, candidate_fuel, candidate_size, candidate_reason in attempts:
            if candidate_subtype is None:
                continue
            selected = self._find(mode, candidate_subtype, candidate_fuel, candidate_size)
            if selected is not None:
                reason = candidate_reason
                break
        if selected is None:
            raise LookupError(f"no emission factor resolved for mode={mode}, subtype={subtype}, fuel={fuel_type}, size={vehicle_size}")
        fallback = reason not in {"exact fuel and size", "exact bus subtype", "exact rail subtype", "policy default"}
        return {
            "factor_value": float(selected["factor_value"]),
            "unit": selected["normalized_unit"],
            "canonical_mode": mode,
            "resolved_subtype": selected["emission_subtype"],
            "source": selected["source_name"],
            "source_year": int(selected["source_year"]),
            "source_category": selected["source_category"],
            "source_row_identifier": selected["source_row_identifier"],
            "fallback_used": fallback,
            "fallback_reason": None if not fallback else reason,
        }
