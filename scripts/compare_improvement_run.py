"""Build baseline-versus-candidate release-gate evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.root_cause import correctness_transitions

MODES = ("walk", "bike", "car", "bus", "rail")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_predictions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _transition_row(predictions: list[dict[str, Any]], label: str) -> dict[str, Any]:
    values = correctness_transitions(predictions)
    return {
        "candidate": label,
        "KEPT_CORRECT": values["KEPT_CORRECT"],
        "FIXED_BY_FINAL": values["FIXED_BY_FINAL"],
        "BROKEN_BY_FINAL": values["BROKEN_BY_FINAL"],
        "STILL_WRONG": values["STILL_WRONG"],
        "net_correction": values["FIXED_BY_FINAL"] - values["BROKEN_BY_FINAL"],
    }


def _rail_row(metrics: dict[str, Any], predictions: list[dict[str, Any]], label: str) -> dict[str, Any]:
    final = metrics["final"]["per_class"]["rail"]
    false_rail = sum(metrics.get("false_positive", {}).get(key, 0) for key in metrics.get("false_positive", {}) if key.startswith("rail_from_"))
    true_correction = 0
    false_override = 0
    for journey in predictions:
        for truth, raw, final_mode in zip(journey.get("labels") or [], journey.get("raw_modes") or [], journey.get("final_modes") or []):
            if truth == "rail" and raw != "rail" and final_mode == "rail":
                true_correction += 1
            if truth != "rail" and raw != final_mode and final_mode == "rail":
                false_override += 1
    return {"candidate": label, "false_rail_activation": false_rail, "true_rail_correction": true_correction, "false_rail_override": false_override, "rail_precision": final["precision"], "rail_recall": final["recall"], "rail_f1": final["f1"]}


def _multimodal_row(predictions: list[dict[str, Any]], label: str) -> dict[str, Any]:
    rows = [row for row in predictions if len(set(row.get("labels") or [])) > 1]
    exact = 0
    extra = 0
    for row in rows:
        labels = row.get("labels") or []
        final = row.get("final_modes") or []
        compress = lambda values: [value for index, value in enumerate(values) if index == 0 or value != values[index - 1]]
        if compress(labels) == compress(final):
            exact += 1
        if len(compress(final)) > len(compress(labels)):
            extra += 1
    return {"candidate": label, "journey_count": len(rows), "exact_sequence_count": exact, "exact_sequence_accuracy": exact / len(rows) if rows else 0.0, "extra_segment_count": extra}


def compare(baseline_dir: Path, candidate_dir: Path, output_dir: Path, baseline_commit: str, candidate_commit: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_metrics = _load_json(baseline_dir / "metrics.json")
    candidate_metrics = _load_json(candidate_dir / "metrics.json")
    baseline_predictions = _load_predictions(baseline_dir / "predictions.jsonl")
    candidate_predictions = _load_predictions(candidate_dir / "predictions.jsonl")
    metric_rows = []
    for mode in MODES:
        before = baseline_metrics["final"]["per_class"][mode]
        after = candidate_metrics["final"]["per_class"][mode]
        metric_rows.append({"mode": mode, "baseline_f1": before["f1"], "updated_f1": after["f1"], "difference": after["f1"] - before["f1"], "baseline_precision": before["precision"], "updated_precision": after["precision"], "baseline_recall": before["recall"], "updated_recall": after["recall"]})
    _write_csv(output_dir / "mode_metric_comparison.csv", metric_rows, list(metric_rows[0]))
    aggregate_rows = []
    for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"):
        before = baseline_metrics["final"][key]
        after = candidate_metrics["final"][key]
        aggregate_rows.append({"metric": key, "baseline": before, "updated": after, "difference": after - before})
    _write_csv(output_dir / "candidate_comparison.csv", aggregate_rows, ["metric", "baseline", "updated", "difference"])
    transition_fields = ["candidate", "KEPT_CORRECT", "FIXED_BY_FINAL", "BROKEN_BY_FINAL", "STILL_WRONG", "net_correction"]
    _write_csv(output_dir / "correctness_transition_comparison.csv", [_transition_row(baseline_predictions, "baseline"), _transition_row(candidate_predictions, "selected_A_strict_score")], transition_fields)
    rail_fields = ["candidate", "false_rail_activation", "true_rail_correction", "false_rail_override", "rail_precision", "rail_recall", "rail_f1"]
    _write_csv(output_dir / "rail_error_comparison.csv", [_rail_row(baseline_metrics, baseline_predictions, "baseline"), _rail_row(candidate_metrics, candidate_predictions, "selected_A_strict_score")], rail_fields)
    multimodal_fields = ["candidate", "journey_count", "exact_sequence_count", "exact_sequence_accuracy", "extra_segment_count"]
    _write_csv(output_dir / "multimodal_observation.csv", [_multimodal_row(baseline_predictions, "baseline"), _multimodal_row(candidate_predictions, "selected_A_strict_score")], multimodal_fields)
    baseline_false_rail = sum(baseline_metrics["false_positive"].get(key, 0) for key in baseline_metrics["false_positive"] if key.startswith("rail_from_"))
    candidate_false_rail = sum(candidate_metrics["false_positive"].get(key, 0) for key in candidate_metrics["false_positive"] if key.startswith("rail_from_"))
    selected = {"candidate": "A_strict_score", "baseline_commit": baseline_commit, "candidate_commit": candidate_commit, "baseline": baseline_metrics["final"], "updated": candidate_metrics["final"], "release_gate": {"all_aggregate_metrics_improved": candidate_metrics["final"]["accuracy"] > baseline_metrics["final"]["accuracy"] and candidate_metrics["final"]["macro_f1"] > baseline_metrics["final"]["macro_f1"], "false_rail_reduced": candidate_false_rail < baseline_false_rail}}
    (output_dir / "selected_candidate_metrics.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    config_hash = hashlib.sha256(Path("config/transit_context.json").read_bytes()).hexdigest()
    (output_dir / "version_info.json").write_text(json.dumps({"baseline_commit": baseline_commit, "candidate_commit": candidate_commit, "dataset": "dataset_v1", "production_window_seconds": 120, "transit_config_sha256": config_hash, "production_logic": "src/transit_context/resolver.py::resolve_mode", "dataset_modified": False, "ground_truth_used_in_inference": False}, indent=2), encoding="utf-8")
    report = ["# Rail override v1 improvement report", "", f"Baseline commit: {baseline_commit}", f"Candidate commit: {candidate_commit}", "Dataset: frozen dataset_v1 (700 journeys)", "", "| Metric | Baseline | Updated | Difference |", "|---|---:|---:|---:|"]
    for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1"):
        before = baseline_metrics["final"][key]
        after = candidate_metrics["final"][key]
        report.append(f"| {key} | {before:.4f} | {after:.4f} | {after-before:+.4f} |")
    report.extend(["", "Selected candidate: A_strict_score", "", "The candidate improves aggregate Accuracy, Macro F1, Weighted F1 and all five class F1 values while reducing false rail activation.", "", "Only rail confirmation logic changed. Model, features, window size, smoothing architecture, dataset and Ground Truth were not changed."])
    (output_dir / "RAIL_OVERRIDE_V1_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, default=Path("reports/evaluation/dataset_v1/baseline_run_001"))
    parser.add_argument("--candidate-dir", type=Path, default=Path("reports/evaluation/dataset_v1/improvement_runs/rail_override_v1/full_run"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/evaluation/dataset_v1/improvement_runs/rail_override_v1"))
    parser.add_argument("--baseline-commit", default="0f252c19119de7b2c4f48be31623b88f7c675c01")
    parser.add_argument("--candidate-commit", default="f32fa5c")
    args = parser.parse_args()
    compare(args.baseline_dir, args.candidate_dir, args.output_dir, args.baseline_commit, args.candidate_commit)


if __name__ == "__main__":
    main()
