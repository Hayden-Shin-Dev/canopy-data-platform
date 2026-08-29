"""Evaluation-only root-cause aggregations for a frozen baseline run.

The functions in this module consume stored predictions and never participate
in production inference.  Ground-truth values are used only after a run has
completed, which keeps the blind baseline immutable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

MODES = ("walk", "bike", "car", "bus", "rail")
TRANSIT_MODES = {"bus", "rail"}


def _compress(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not result or result[-1] != value:
            result.append(value)
    return result


def _rows(predictions: Iterable[Mapping[str, Any]]) -> Iterable[dict[str, str]]:
    """Yield one row per scored prediction window."""
    for journey in predictions:
        labels = journey.get("labels") or []
        raw = journey.get("raw_modes") or []
        final = journey.get("final_modes") or []
        for index, (truth, raw_mode, final_mode) in enumerate(zip(labels, raw, final)):
            yield {
                "trip_id": str(journey.get("trip_id", "")),
                "scenario_category": str(journey.get("scenario_category", "")),
                "noise_profile": str(journey.get("noise_profile", "")),
                "hard_case_type": str(journey.get("hard_case_type") or ""),
                "window_index": str(index),
                "ground_truth": str(truth),
                "raw_mode": str(raw_mode),
                "final_mode": str(final_mode),
            }


def raw_final_transition_matrix(predictions: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    matrix = {raw: {final: 0 for final in MODES} for raw in MODES}
    for row in _rows(predictions):
        if row["raw_mode"] in matrix and row["final_mode"] in matrix[row["raw_mode"]]:
            matrix[row["raw_mode"]][row["final_mode"]] += 1
    return matrix


def correctness_transitions(predictions: Iterable[Mapping[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in _rows(predictions):
        raw_correct = row["raw_mode"] == row["ground_truth"]
        final_correct = row["final_mode"] == row["ground_truth"]
        if raw_correct and final_correct:
            counts["KEPT_CORRECT"] += 1
        elif not raw_correct and final_correct:
            counts["FIXED_BY_FINAL"] += 1
        elif raw_correct and not final_correct:
            counts["BROKEN_BY_FINAL"] += 1
        else:
            counts["STILL_WRONG"] += 1
    return counts


def per_mode_correctness(predictions: Iterable[Mapping[str, Any]]) -> dict[str, Counter[str]]:
    result = {mode: Counter() for mode in MODES}
    for row in _rows(predictions):
        mode = row["ground_truth"]
        if mode not in result:
            continue
        raw_correct = row["raw_mode"] == mode
        final_correct = row["final_mode"] == mode
        if raw_correct and final_correct:
            key = "kept_correct"
        elif not raw_correct and final_correct:
            key = "fixed_by_final"
        elif raw_correct and not final_correct:
            key = "broken_by_final"
        else:
            key = "still_wrong"
        result[mode][key] += 1
    return result


def hybrid_interventions(predictions: Iterable[Mapping[str, Any]]) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in _rows(predictions):
        if row["raw_mode"] == row["final_mode"]:
            continue
        raw_correct = row["raw_mode"] == row["ground_truth"]
        final_correct = row["final_mode"] == row["ground_truth"]
        if final_correct and not raw_correct:
            result["helpful"] += 1
        elif raw_correct and not final_correct:
            result["harmful"] += 1
        else:
            result["neutral_wrong_to_wrong"] += 1
    result["total"] = sum(result.values())
    return result


def transit_error_counts(predictions: Iterable[Mapping[str, Any]]) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in _rows(predictions):
        truth, final = row["ground_truth"], row["final_mode"]
        if truth not in TRANSIT_MODES and final in TRANSIT_MODES:
            result[f"false_{final}"] += 1
        if truth in TRANSIT_MODES and final not in TRANSIT_MODES:
            result[f"missing_{truth}"] += 1
        if row["raw_mode"] != final:
            result["resolver_or_smoothing_changes"] += 1
    return result


def scenario_metrics(predictions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _rows(predictions):
        groups[row["scenario_category"]].append(row)
    result = []
    for scenario, rows in sorted(groups.items()):
        raw = sum(row["raw_mode"] == row["ground_truth"] for row in rows)
        final = sum(row["final_mode"] == row["ground_truth"] for row in rows)
        result.append({
            "scenario": scenario,
            "window_count": len(rows),
            "raw_accuracy": raw / len(rows) if rows else 0.0,
            "final_accuracy": final / len(rows) if rows else 0.0,
            "difference": (final - raw) / len(rows) if rows else 0.0,
        })
    return result


def noise_metrics(predictions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _rows(predictions):
        groups[row["noise_profile"]].append(row)
    result = []
    for noise, rows in sorted(groups.items()):
        raw = sum(row["raw_mode"] == row["ground_truth"] for row in rows)
        final = sum(row["final_mode"] == row["ground_truth"] for row in rows)
        result.append({
            "noise_profile": noise,
            "window_count": len(rows),
            "raw_accuracy": raw / len(rows) if rows else 0.0,
            "final_accuracy": final / len(rows) if rows else 0.0,
        })
    return result


def multimodal_failures(predictions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for journey in predictions:
        labels = journey.get("labels") or []
        final = journey.get("final_modes") or []
        raw = journey.get("raw_modes") or []
        if len(set(labels)) <= 1:
            continue
        truth_seq = _compress(labels)
        raw_seq = _compress(raw)
        final_seq = _compress(final)
        if final_seq == truth_seq:
            failure = "MATCH"
        elif not final_seq or final_seq[0] != truth_seq[0]:
            failure = "WRONG_INITIAL_MODE"
        elif len(final_seq) < len(truth_seq):
            failure = "MISSING_SEGMENT"
        elif len(final_seq) > len(truth_seq):
            failure = "EXTRA_SEGMENT"
        elif final_seq[-1] != truth_seq[-1]:
            failure = "WRONG_FINAL_MODE"
        elif final_seq != raw_seq:
            failure = "TRANSITION_CORRECTION_OR_REGRESSION"
        else:
            failure = "WRONG_INTERMEDIATE_MODE"
        result.append({
            "trip_id": journey.get("trip_id", ""),
            "ground_truth_sequence": "->".join(truth_seq),
            "raw_sequence": "->".join(raw_seq),
            "final_sequence": "->".join(final_seq),
            "failure_type": failure,
        })
    return result


def first_error_stage(journey: Mapping[str, Any]) -> str:
    labels = journey.get("labels") or []
    raw = journey.get("raw_modes") or []
    final = journey.get("final_modes") or []
    for index, truth in enumerate(labels):
        raw_mode = raw[index] if index < len(raw) else ""
        final_mode = final[index] if index < len(final) else ""
        if final_mode == truth:
            continue
        if raw_mode != truth:
            return "RAW_ML"
        if raw_mode != final_mode:
            return "TRANSIT_CONTEXT_OR_RESOLVER"
        return "SMOOTHING_OR_SEGMENTATION"
    return "NONE"


def representative_failures(predictions: Iterable[Mapping[str, Any]], limit: int = 25) -> list[dict[str, Any]]:
    rows = []
    for journey in predictions:
        labels = journey.get("labels") or []
        raw = journey.get("raw_modes") or []
        final = journey.get("final_modes") or []
        wrong = sum(mode != truth for mode, truth in zip(final, labels))
        if wrong:
            rows.append({
                "trip_id": journey.get("trip_id", ""),
                "ground_truth": "->".join(_compress(labels)),
                "raw_prediction": "->".join(_compress(raw)),
                "final_prediction": "->".join(_compress(final)),
                "wrong_windows": wrong,
                "failure_stage": first_error_stage(journey),
                "scenario_category": journey.get("scenario_category", ""),
            })
    return sorted(rows, key=lambda row: (-row["wrong_windows"], row["trip_id"]))[:limit]
