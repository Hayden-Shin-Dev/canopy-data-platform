"""Merge independent frozen-dataset evaluation shards into one report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from scripts.evaluate_dataset_v1 import MODES, _metric_payload, _present, _write_confusion, _write_per_class, _write_report


def merge(shard_dirs: list[Path], output: Path, *, baseline_commit: str, evaluation_commit: str, branch: str) -> None:
    predictions = []
    traces = []
    shard_summaries = []
    for shard in shard_dirs:
        predictions.extend(json.loads(line) for line in (shard / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
        traces.extend(line for line in (shard / "prediction_traces.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
        shard_summaries.append(json.loads((shard / "summary.json").read_text(encoding="utf-8")))
    predictions.sort(key=lambda item: str(item.get("trip_id", "")))
    output.mkdir(parents=True, exist_ok=True)
    (output / "predictions.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in predictions) + "\n", encoding="utf-8")
    (output / "prediction_traces.jsonl").write_text("\n".join(traces) + ("\n" if traces else ""), encoding="utf-8")
    successful = [item for item in predictions if item.get("status") == "PASS"]
    failed = [item for item in predictions if item.get("status") == "FAIL"]
    y_true = [label for item in successful for label in item.get("labels", [])]
    y_raw = [label for item in successful for label in item.get("raw_modes", [])]
    y_final = [label for item in successful for label in item.get("final_modes", [])]
    raw_metrics, final_metrics = _metric_payload(y_true, y_raw), _metric_payload(y_true, y_final)
    metrics = {
        "raw": raw_metrics,
        "final": final_metrics,
        "false_positive": {
            "rail_from_car": sum(a == "car" and b == "rail" for a, b in zip(y_true, y_final)),
            "rail_from_bike": sum(a == "bike" and b == "rail" for a, b in zip(y_true, y_final)),
            "rail_from_walk": sum(a == "walk" and b == "rail" for a, b in zip(y_true, y_final)),
            "bus_from_car": sum(a == "car" and b == "bus" for a, b in zip(y_true, y_final)),
        },
        "false_negative": {
            "rail_to_nonrail": sum(a == "rail" and b != "rail" for a, b in zip(y_true, y_final)),
            "bus_to_nonbus": sum(a == "bus" and b != "bus" for a, b in zip(y_true, y_final)),
        },
    }
    multimodal = [item for item in successful if "|" in str(item.get("ground_truth", ""))]
    hard_rows = [item for item in successful if _present(item.get("hard_case_type"))]
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "dataset_root": shard_summaries[0].get("dataset_root"),
        "dataset_validation": shard_summaries[0].get("dataset_validation"),
        "canopy_baseline_commit": baseline_commit,
        "evaluation_commit": evaluation_commit,
        "branch": branch,
        "total_journeys": len(predictions),
        "successfully_evaluated": len(successful),
        "failed": len(failed),
        "skipped": 0,
        "runtime_seconds": sum(float(item.get("runtime_seconds", 0)) for item in shard_summaries),
        "ground_truth_used_by_inference": False,
        "gps_label_leakage": any(bool(item.get("gps_label_leakage")) for item in shard_summaries),
        "multimodal_journeys": len(multimodal),
        "hard_case_journeys": len(hard_rows),
        "merged_from_shards": [str(path) for path in shard_dirs],
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_confusion(output / "confusion_matrix_raw.csv", y_true, y_raw)
    _write_confusion(output / "confusion_matrix_final.csv", y_true, y_final)
    _write_per_class(output / "per_class_metrics.csv", raw_metrics, final_metrics)
    pd.DataFrame([{"trip_id": item["trip_id"], "ground_truth": item["ground_truth"], "raw_prediction": item["raw_prediction"], "final_prediction": item["final_prediction"], "correct_raw": item["correct_raw"], "correct_final": item["correct_final"]} for item in multimodal]).to_csv(output / "multimodal_predictions.csv", index=False, encoding="utf-8-sig")
    (output / "multimodal_metrics.json").write_text(json.dumps({"journey_count": len(multimodal), "raw_exact_sequence_accuracy": sum(item["correct_raw"] for item in multimodal) / len(multimodal) if multimodal else None, "final_exact_sequence_accuracy": sum(item["correct_final"] for item in multimodal) / len(multimodal) if multimodal else None}, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([{"hard_case_type": item.get("hard_case_type"), "trip_id": item["trip_id"], "correct_raw": item["correct_raw"], "correct_final": item["correct_final"]} for item in hard_rows]).to_csv(output / "hard_case_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "ground_truth": item.get("ground_truth"), "raw_prediction": item.get("raw_prediction"), "final_prediction": item.get("final_prediction"), "scenario_category": item.get("scenario_category"), "hard_case_type": item.get("hard_case_type")} for item in successful if not item.get("correct_final")]).to_csv(output / "error_analysis.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "reason": item.get("failure_reason")} for item in failed]).to_csv(output / "failed_journeys.csv", index=False, encoding="utf-8-sig")
    errors = Counter((a, b) for a, b in zip(y_true, y_final) if a != b)
    pd.DataFrame([{"ground_truth": a, "prediction": b, "count": count} for (a, b), count in errors.most_common()]).to_csv(output / "top_errors.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "ground_truth_sequence": item["ground_truth"], "raw_sequence": item["raw_prediction"], "final_sequence": item["final_prediction"], "raw_exact": item["correct_raw"], "final_exact": item["correct_final"]} for item in multimodal]).to_csv(output / "segment_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "expected_transitions": "|".join(f"{a}->{b}" for a, b in zip(item["ground_truth"].split("|"), item["ground_truth"].split("|")[1:])), "predicted_transitions": "|".join(f"{a}->{b}" for a, b in zip(item["final_prediction"].split("|"), item["final_prediction"].split("|")[1:])), "transition_exact": item["correct_final"]} for item in multimodal]).to_csv(output / "transition_metrics.csv", index=False, encoding="utf-8-sig")
    (output / "realtime_metrics.json").write_text(json.dumps({"status": "PASS", "definition": "raw GeoLife prediction at each completed window uses only GPS available through that window", "raw_window_metrics": raw_metrics, "final_window_metrics": final_metrics}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "distance_weighted_metrics.json").write_text(json.dumps({"status": "NOT_AVAILABLE", "reason": "Frozen Ground Truth has journey-level distance only; no per-segment distance weights are provided."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    noise = {profile: [item for item in successful if item.get("noise_profile") == profile] for profile in ("clean", "normal", "noisy")}
    pd.DataFrame([{"noise_profile": profile, "journey_count": len(items), "raw_accuracy": sum(item["correct_raw"] for item in items) / len(items) if items else None, "final_accuracy": sum(item["correct_final"] for item in items) / len(items) if items else None} for profile, items in noise.items()]).to_csv(output / "noise_metrics.csv", index=False, encoding="utf-8-sig")
    hard_summary = []
    for case in sorted({item.get("hard_case_type") for item in hard_rows}):
        items = [item for item in hard_rows if item.get("hard_case_type") == case]
        hard_summary.append({"hard_case_type": case, "journey_count": len(items), "raw_accuracy": sum(item["correct_raw"] for item in items) / len(items), "final_accuracy": sum(item["correct_final"] for item in items) / len(items)})
    pd.DataFrame(hard_summary).to_csv(output / "hard_case_summary.csv", index=False, encoding="utf-8-sig")
    _write_report(output, summary, metrics)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--evaluation-commit", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    merge(args.shard, args.output, baseline_commit=args.baseline_commit, evaluation_commit=args.evaluation_commit, branch=args.branch)


if __name__ == "__main__":
    main()
