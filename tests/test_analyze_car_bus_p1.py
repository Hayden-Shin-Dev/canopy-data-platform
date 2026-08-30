from __future__ import annotations

import copy

from scripts.analyze_car_bus_p1 import (
    bus_evidence,
    confusion,
    correctness_for_mode,
    failure_pareto,
)


def _journey(labels, raw, final, scores=None, ground_truth="multimodal"):
    scores = scores or [0.0] * len(labels)
    return {
        "ground_truth": ground_truth,
        "labels": labels,
        "raw_modes": raw,
        "final_modes": final,
        "traces": [{"bus_context_score": score} for score in scores],
    }


def test_confusion_aggregates_all_car_bus_pairs():
    rows = confusion(
        [_journey(["car", "bus"], ["bus", "car"], ["car", "bus"])],
        "raw",
    )
    counts = {(row["ground_truth"], row["prediction"]): row["count"] for row in rows}
    assert counts[("car", "bus")] == 1
    assert counts[("bus", "car")] == 1
    assert counts[("car", "car")] == 0


def test_bus_evidence_coverage_uses_explicit_analysis_bins():
    coverage, not_bus = bus_evidence(
        [_journey(["bus", "bus", "bus"], ["bus"] * 3, ["bus", "car", "walk"], [0.0, 0.30, 0.80])]
    )
    by_level = {row["evidence_level"]: row["window_count"] for row in coverage}
    assert by_level == {"none": 1, "weak": 1, "strong": 1}
    assert sum(row["window_count"] for row in coverage) == 3
    assert {row["final_mode"]: row["count"] for row in not_bus} == {"car": 1, "walk": 1}


def test_correctness_transition_reports_zero_categories():
    result = correctness_for_mode(
        [_journey(["car", "car"], ["car", "walk"], ["car", "car"])], "car"
    )
    assert result == {
        "kept_correct": 1,
        "fixed_by_final": 1,
        "broken_by_final": 0,
        "still_wrong": 0,
    }


def test_failure_pareto_shares_sum_to_one():
    rows = failure_pareto(
        [_journey(["bus", "bus", "bus"], ["car", "walk", "bus"], ["car", "walk", "rail"])],
        "bus",
    )
    assert sum(row["count"] for row in rows) == 3
    assert abs(sum(row["share"] for row in rows) - 1.0) < 1e-9
    assert {row["cause"] for row in rows} == {
        "raw_predicts_car",
        "raw_predicts_walk_or_bike",
        "transit_override_after_raw_correct",
    }


def test_aggregation_does_not_use_journey_ground_truth_for_inference():
    journey = _journey(["bus"], ["car"], ["car"], ground_truth="car")
    changed = copy.deepcopy(journey)
    changed["ground_truth"] = "bus"
    assert confusion([journey], "raw") == confusion([changed], "raw")
    assert failure_pareto([journey], "bus") == failure_pareto([changed], "bus")

