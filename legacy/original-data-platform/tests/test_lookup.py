from __future__ import annotations

import pandas as pd
import pytest

from src.ktdb.lookup import build_population_lookup, normalize_mode_probabilities


CONTEXT = {
    "weekday": "월",
    "time_band": "daytime",
    "origin_sido": "서울",
    "origin_sigungu": "강남구",
    "od_scope": "same_sido",
    "purpose": "출근",
    "commute_direction": "to_work",
}


def test_normalize_mode_probabilities_fills_all_classes() -> None:
    probabilities = normalize_mode_probabilities({"car": 3, "walk": 1})

    assert probabilities["car"] == pytest.approx(0.75)
    assert probabilities["walk"] == pytest.approx(0.25)
    assert probabilities["rail"] == 0
    assert sum(probabilities.values()) == pytest.approx(1.0)


def test_lookup_keeps_exact_and_fallback_levels() -> None:
    rows = [
        {**CONTEXT, "actual_mode": "car"},
        {**CONTEXT, "actual_mode": "walk"},
        {**{**CONTEXT, "weekday": "화"}, "actual_mode": "rail"},
    ]
    lookup = build_population_lookup(
        pd.DataFrame(rows),
        min_samples=1,
        fallback_levels=[
            ("weekday", "time_band"),
            ("weekday",),
        ],
    )

    assert set(lookup["context_level"]) == {"weekday|time_band", "weekday"}
    exact = lookup[lookup["context_level"].eq("weekday|time_band")]
    monday = exact[exact["weekday"].eq("월")].iloc[0]
    assert monday["sample_count"] == 2
    assert monday["car_probability"] == pytest.approx(0.5)
    assert monday["walk_probability"] == pytest.approx(0.5)


def test_lookup_rejects_unknown_mode() -> None:
    frame = pd.DataFrame([{**CONTEXT, "actual_mode": "taxi"}])

    with pytest.raises(ValueError, match="5-class"):
        build_population_lookup(frame, min_samples=1)
