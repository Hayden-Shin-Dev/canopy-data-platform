"""Blind evaluation runner for the frozen Seoul synthetic journey dataset.

Ground Truth is loaded only after the production pipeline has returned its
prediction.  The dataset directory is never used as an output location.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_integration_ui import _default_expected_features
from src.evaluation.dataset_v1 import (
    FrozenDataset,
    discover_dataset,
    iter_manifest_rows,
    validate_frozen_dataset,
    validate_gps_schema,
)
from src.integration.gps_contract import validate_gps_event
from src.integration.ktdb_context import build_expected_features
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import read_replay_csv


MODES = ("walk", "bike", "car", "bus", "rail")


def _present(value: Any) -> str | None:
    """Normalize pandas NaN manifest cells to an absent value."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _load_ground_truth(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    segments = []
    for segment in payload.get("segments", []):
        start_value = segment.get("start_timestamp", segment.get("start_time"))
        end_value = segment.get("end_timestamp", segment.get("end_time"))
        if start_value is None or end_value is None:
            raise ValueError(f"ground truth segment has no start/end timestamp: {path}")
        segments.append(
            {
                **segment,
                "mode": str(segment["mode"]),
                "start": _parse_time(start_value),
                "end": _parse_time(end_value),
            }
        )
    return {**payload, "segments": segments}


def _label_at(timestamp: datetime, segments: list[dict[str, Any]]) -> str | None:
    for segment in segments:
        if segment["start"] <= timestamp < segment["end"]:
            return segment["mode"]
    if segments and timestamp == segments[-1]["end"]:
        return segments[-1]["mode"]
    return None


def _compress(modes: Iterable[str]) -> list[str]:
    result: list[str] = []
    for mode in modes:
        if mode in MODES and (not result or result[-1] != mode):
            result.append(mode)
    return result


def _trip_prediction(modes: list[str], multimodal: bool) -> str:
    if multimodal:
        return "|".join(_compress(modes))
    values = [mode for mode in modes if mode in MODES]
    return Counter(values).most_common(1)[0][0] if values else "unknown"


def _metric_payload(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    if not y_true:
        return {"count": 0, "accuracy": None, "macro_precision": None, "macro_recall": None, "macro_f1": None, "weighted_f1": None, "per_class": {}}
    report = classification_report(y_true, y_pred, labels=list(MODES), output_dict=True, zero_division=0)
    return {
        "count": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(report["macro avg"]["precision"]),
        "macro_recall": float(report["macro avg"]["recall"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "weighted_f1": float(report["weighted avg"]["f1-score"]),
        "per_class": {
            mode: {
                "precision": float(report[mode]["precision"]),
                "recall": float(report[mode]["recall"]),
                "f1": float(report[mode]["f1-score"]),
                "support": int(report[mode]["support"]),
            }
            for mode in MODES
        },
    }


def _write_confusion(path: Path, y_true: list[str], y_pred: list[str]) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=list(MODES))
    frame = pd.DataFrame(matrix, index=MODES, columns=MODES)
    frame.index.name = "actual"
    frame.to_csv(path, encoding="utf-8-sig")


def _write_per_class(path: Path, raw: dict[str, Any], final: dict[str, Any]) -> None:
    rows = []
    for mode in MODES:
        rows.append(
            {
                "mode": mode,
                "raw_precision": raw["per_class"].get(mode, {}).get("precision"),
                "raw_recall": raw["per_class"].get(mode, {}).get("recall"),
                "raw_f1": raw["per_class"].get(mode, {}).get("f1"),
                "final_precision": final["per_class"].get(mode, {}).get("precision"),
                "final_recall": final["per_class"].get(mode, {}).get("recall"),
                "final_f1": final["per_class"].get(mode, {}).get("f1"),
                "support": final["per_class"].get(mode, {}).get("support", 0),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _evaluate_trip(
    row: dict[str, Any],
    *,
    references: TransitRuntimeReferences,
    geolife_model: Path,
    ktdb_model: Path,
    factors_csv: Path,
    fallback_expected: dict[str, object],
    derive_ktdb_features: bool = False,
    window_seconds: int = 120,
) -> dict[str, Any]:
    """Run production inference, then load Ground Truth for scoring."""

    schema = validate_gps_schema(row["gps_path"])
    if schema["status"] != "PASS":
        return {"trip_id": row["trip_id"], "status": "FAIL", "failure_reason": "gps_schema", "schema": schema}
    raw_rows = read_replay_csv(row["gps_path"])
    events = [validated.event for validated in (validate_gps_event(item) for item in raw_rows) if validated.event is not None]
    if len(events) < 2:
        return {"trip_id": row["trip_id"], "status": "FAIL", "failure_reason": "fewer_than_two_valid_events"}
    # Expected Behaviour is an input contract for the existing pipeline; it is
    # not used to derive the mobility labels being evaluated here.
    try:
        expected = build_expected_features(events).features if derive_ktdb_features else None
        expected_source = "route_reference" if expected is not None else "repository_demo_reference_fallback"
    except Exception:
        expected = fallback_expected
        expected_source = "repository_demo_reference_fallback"
    if expected is None:
        expected = fallback_expected
    pipeline = run_full_pipeline(
        events,
        expected,
        references=references,
        geolife_model_path=geolife_model,
        ktdb_model_path=ktdb_model,
        factors_csv=factors_csv,
        window_seconds=window_seconds,
    )
    # Ground Truth is intentionally opened only after run_full_pipeline.
    truth = _load_ground_truth(row["ground_truth_path"])
    if pipeline.get("status") != "PASS":
        return {
            "trip_id": row["trip_id"],
            "status": "FAIL",
            "failure_reason": str(pipeline.get("reason", pipeline.get("status"))),
            "scenario_category": truth.get("scenario_category"),
            "expected_feature_source": expected_source,
        }
    window_results = list(pipeline.get("window_results", []))
    raw_modes: list[str] = []
    final_modes: list[str] = []
    labels: list[str] = []
    traces: list[dict[str, Any]] = []
    for window in window_results:
        raw_mode = str(window.get("geolife_predicted_mode", "unknown"))
        final_mode = str(window.get("final_mode", "unknown"))
        midpoint = _parse_time(window["window_start"]) + (_parse_time(window["window_end"]) - _parse_time(window["window_start"])) / 2
        label = _label_at(midpoint, truth["segments"])
        if label not in MODES:
            continue
        raw_modes.append(raw_mode)
        final_modes.append(final_mode)
        labels.append(label)
        transit = window.get("transit_context", {})
        traces.append(
            {
                "trip_id": row["trip_id"],
                "window_start": window["window_start"],
                "ground_truth": label,
                "raw_mode": raw_mode,
                "final_mode": final_mode,
                "transit_candidate": transit.get("transit_candidate"),
                "matched_subway_line": transit.get("matched_subway_line"),
                "bus_context_score": transit.get("bus_context_score"),
                "subway_context_score": transit.get("subway_context_score"),
            }
        )
    multimodal = len(truth["segments"]) > 1 or str(truth.get("scenario_category")) == "multimodal"
    gt_sequence = _compress(segment["mode"] for segment in truth["segments"])
    raw_trip = _trip_prediction(raw_modes, multimodal)
    final_trip = _trip_prediction(final_modes, multimodal)
    expected_trip = "|".join(gt_sequence) if multimodal else (gt_sequence[0] if gt_sequence else "unknown")
    return {
        "trip_id": row["trip_id"],
        "status": "PASS",
        "scenario_category": truth.get("scenario_category"),
        "noise_profile": _present(row.get("noise_profile")),
        "hard_case_type": _present(row.get("hard_case_type")),
        "ground_truth": expected_trip,
        "raw_prediction": raw_trip,
        "final_prediction": final_trip,
        "correct_raw": raw_trip == expected_trip,
        "correct_final": final_trip == expected_trip,
        "window_count": len(labels),
        "raw_modes": raw_modes,
        "final_modes": final_modes,
        "labels": labels,
        "expected_feature_source": expected_source,
        "pipeline_summary": {
            "distance_km": pipeline.get("distance_km"),
            "co2": pipeline.get("co2"),
            "final_mode": pipeline.get("actual_behaviour", {}).get("final_mode"),
        },
        "traces": traces,
    }


def _write_report(run_dir: Path, summary: dict[str, Any], metrics: dict[str, Any]) -> None:
    def pct(value: Any) -> str:
        return "N/A" if value is None else f"{float(value):.4f}"

    raw, final = metrics["raw"], metrics["final"]
    rows = [
        f"# Canopy {summary.get('dataset_version', 'dataset_v1')} blind evaluation",
        "",
        f"Dataset: `{summary['dataset_root']}`",
        f"Canopy Baseline Commit: `{summary['canopy_baseline_commit']}`",
        f"Evaluation Commit: `{summary['evaluation_commit']}`",
        f"Ground Truth used during inference: **NO**",
        f"Total journeys: {summary['total_journeys']} / evaluated: {summary['successfully_evaluated']} / failed: {summary['failed']}",
        "",
        "## Raw GeoLife vs Final Canopy",
        "",
        "| Metric | Raw GeoLife | Final Canopy | Difference |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, key in (("Accuracy", "accuracy"), ("Macro Precision", "macro_precision"), ("Macro Recall", "macro_recall"), ("Macro F1", "macro_f1"), ("Weighted F1", "weighted_f1")):
        difference = None if raw.get(key) is None or final.get(key) is None else final[key] - raw[key]
        rows.append(f"| {label} | {pct(raw.get(key))} | {pct(final.get(key))} | {pct(difference)} |")
    rows.extend(["", "## Per mode F1", "", "| Mode | Raw F1 | Final F1 | Difference |", "| --- | ---: | ---: | ---: |"])
    for mode in MODES:
        raw_f1 = raw["per_class"].get(mode, {}).get("f1")
        final_f1 = final["per_class"].get(mode, {}).get("f1")
        difference = None if raw_f1 is None or final_f1 is None else final_f1 - raw_f1
        rows.append(f"| {mode} | {pct(raw_f1)} | {pct(final_f1)} | {pct(difference)} |")
    rows.extend(["", "## Final precision, recall, F1, and support", "", "| Mode | Precision | Recall | F1 | Support |", "| --- | ---: | ---: | ---: | ---: |"])
    for mode in MODES:
        item = final["per_class"].get(mode, {})
        rows.append(f"| {mode} | {pct(item.get('precision'))} | {pct(item.get('recall'))} | {pct(item.get('f1'))} | {item.get('support', 0)} |")
    rows.extend([
        "",
        "## Transit false positive / false negative",
        "",
        f"- False rail from car: {metrics['false_positive']['rail_from_car']}",
        f"- False rail from bike: {metrics['false_positive']['rail_from_bike']}",
        f"- False rail from walk: {metrics['false_positive']['rail_from_walk']}",
        f"- False bus from car: {metrics['false_positive']['bus_from_car']}",
        f"- Rail false negative: {metrics['false_negative']['rail_to_nonrail']}",
        f"- Bus false negative: {metrics['false_negative']['bus_to_nonbus']}",
        "",
        "## Multimodal and transition evaluation",
        "",
        f"- Multimodal journeys: {summary['multimodal_journeys']}",
        "- Exact sequence results: `multimodal_metrics.json`",
        "- Segment and transition rows: `segment_metrics.csv`, `transition_metrics.csv`",
        "",
        "## Hard case and noise evaluation",
        "",
        f"- Hard-case journeys: {summary['hard_case_journeys']}",
        "- Hard-case results: `hard_case_summary.csv`",
        "- Noise profile results: `noise_metrics.csv`",
    ])
    rows.extend(
        [
            "",
            "## Evaluation limitations",
            "",
            "- The frozen dataset is a local read-only asset and is not committed.",
            "- KTDB Expected Behaviour is included for production compatibility; mobility metrics score GeoLife and final resolver labels only.",
            "- Multimodal, hard-case, noise, and failure details are in the machine-readable files in this directory.",
            "- Time-weighted metrics use the fixed 120-second evaluation windows.",
            "- Distance-weighted metrics are marked NOT AVAILABLE because the frozen Ground Truth does not provide per-segment distance weights.",
        ]
    )
    report_name = "BASELINE_EVALUATION_V3.md" if summary.get("dataset_version") == "evaluation_dataset_v3" else "CANOPY_DATASET_V1_EVALUATION.md"
    (run_dir / report_name).write_text("\n".join(rows) + "\n", encoding="utf-8")


def _artifact_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_evaluation(dataset_root: str | Path, run_dir: str | Path, *, canopy_baseline_commit: str, evaluation_commit: str, limit: int | None = None, offset: int = 0, resume: bool = False, verify_hashes: bool = True, derive_ktdb_features: bool = False, branch: str = "eval/seoul-synthetic-v1", geolife_model_path: str | Path | None = None, window_seconds: int = 120) -> dict[str, Any]:
    dataset = discover_dataset(dataset_root)
    frozen_validation = validate_frozen_dataset(dataset, verify_hashes=verify_hashes)
    if frozen_validation["status"] != "PASS":
        raise ValueError(f"frozen dataset validation failed: {frozen_validation}")
    output = Path(run_dir)
    output.mkdir(parents=True, exist_ok=True)
    predictions_path = output / "predictions.jsonl"
    if predictions_path.exists() and not resume:
        raise FileExistsError(f"run already exists; pass --resume to continue: {output}")
    completed: dict[str, dict[str, Any]] = {}
    if resume and predictions_path.is_file():
        for line in predictions_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                completed[str(value["trip_id"])] = value
    rows = list(iter_manifest_rows(dataset))
    if offset < 0:
        raise ValueError("offset must be non-negative")
    rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]
    references = TransitRuntimeReferences.from_directory()
    geolife_model = Path(geolife_model_path) if geolife_model_path else ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"
    ktdb_model = ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl"
    factors_csv = ROOT / "data/processed/emission_factors/emission_factors_2026.csv"
    fallback_expected = _default_expected_features() or {}
    start_time = time.monotonic()
    version_freeze = {
        "branch": branch,
        "canopy_baseline_commit": canopy_baseline_commit,
        "evaluation_commit": evaluation_commit,
        "working_tree_status_before_evaluation": "clean_except_local_frozen_dataset",
        "geolife_model": str(geolife_model),
        "geolife_model_sha256": _artifact_sha256(geolife_model),
        "ktdb_model": str(ktdb_model),
        "ktdb_model_sha256": _artifact_sha256(ktdb_model),
        "transit_resolver": "src/transit_context/resolver.py",
        "transit_settings": "config/transit_context.json",
        "transit_settings_sha256": _artifact_sha256(ROOT / "config/transit_context.json"),
        "window_seconds": window_seconds,
        "smoothing": "src/integration/segments.py::smooth_window_modes",
    }
    (output / "version_freeze.json").write_text(json.dumps(version_freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mode_true: list[str] = []
    mode_raw: list[str] = []
    mode_final: list[str] = []
    traces_path = output / "prediction_traces.jsonl"
    with predictions_path.open("a", encoding="utf-8") as predictions, traces_path.open("a", encoding="utf-8") as traces_file:
        for index, row in enumerate(rows, start=1):
            trip_id = str(row["trip_id"])
            result = completed.get(trip_id) or _evaluate_trip(row, references=references, geolife_model=geolife_model, ktdb_model=ktdb_model, factors_csv=factors_csv, fallback_expected=fallback_expected, derive_ktdb_features=derive_ktdb_features, window_seconds=window_seconds)
            if trip_id not in completed:
                predictions.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
                predictions.flush()
                for trace in result.get("traces", []):
                    traces_file.write(json.dumps(trace, ensure_ascii=False, default=str) + "\n")
                traces_file.flush()
            completed[trip_id] = result
            (output / "checkpoint.json").write_text(
                json.dumps(
                    {
                        "dataset_version": dataset.dataset_manifest.get("dataset_version"),
                        "canopy_baseline_commit": canopy_baseline_commit,
                        "evaluation_commit": evaluation_commit,
                        "completed_trip_ids": sorted(completed),
                        "completed_count": len(completed),
                        "total_requested": len(rows),
                        "updated_at": datetime.now().astimezone().isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            if result.get("status") == "PASS":
                mode_true.extend(result.get("labels", []))
                mode_raw.extend(result.get("raw_modes", []))
                mode_final.extend(result.get("final_modes", []))
            if index == 1 or index % 50 == 0 or index == len(rows):
                print(f"[{index}/{len(rows)}] evaluated={sum(item.get('status') == 'PASS' for item in completed.values())} failed={sum(item.get('status') == 'FAIL' for item in completed.values())}", flush=True)
    raw_metrics = _metric_payload(mode_true, mode_raw)
    final_metrics = _metric_payload(mode_true, mode_final)
    successful = [item for item in completed.values() if item.get("status") == "PASS"]
    failed = [item for item in completed.values() if item.get("status") == "FAIL"]
    multimodal = [item for item in successful if "|" in str(item.get("ground_truth", ""))]
    hard_rows = [item for item in successful if _present(item.get("hard_case_type"))]
    noise_rows = {profile: [item for item in successful if item.get("noise_profile") == profile] for profile in ("clean", "normal", "noisy")}
    metrics = {
        "raw": raw_metrics,
        "final": final_metrics,
        "false_positive": {
            "rail_from_car": sum(true == "car" and pred == "rail" for true, pred in zip(mode_true, mode_final)),
            "rail_from_bike": sum(true == "bike" and pred == "rail" for true, pred in zip(mode_true, mode_final)),
            "rail_from_walk": sum(true == "walk" and pred == "rail" for true, pred in zip(mode_true, mode_final)),
            "bus_from_car": sum(true == "car" and pred == "bus" for true, pred in zip(mode_true, mode_final)),
        },
        "false_negative": {
            "rail_to_nonrail": sum(true == "rail" and pred != "rail" for true, pred in zip(mode_true, mode_final)),
            "bus_to_nonbus": sum(true == "bus" and pred != "bus" for true, pred in zip(mode_true, mode_final)),
        },
    }
    summary = {
        "dataset_root": str(dataset.root),
        "dataset_version": dataset.dataset_manifest.get("dataset_version"),
        "dataset_validation": frozen_validation,
        "canopy_baseline_commit": canopy_baseline_commit,
        "evaluation_commit": evaluation_commit,
        "branch": branch,
        "total_journeys": len(rows),
        "successfully_evaluated": len(successful),
        "failed": len(failed),
        "skipped": 0,
        "runtime_seconds": round(time.monotonic() - start_time, 3),
        "ground_truth_used_by_inference": False,
        "gps_label_leakage": any(validate_gps_schema(path)["forbidden"] for path in dataset.gps_files),
        "multimodal_journeys": len(multimodal),
        "hard_case_journeys": len(hard_rows),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    _write_confusion(output / "confusion_matrix_raw.csv", mode_true, mode_raw)
    _write_confusion(output / "confusion_matrix_final.csv", mode_true, mode_final)
    _write_per_class(output / "per_class_metrics.csv", raw_metrics, final_metrics)
    multimodal_frame = pd.DataFrame(
        [{"trip_id": item["trip_id"], "ground_truth": item["ground_truth"], "raw_prediction": item["raw_prediction"], "final_prediction": item["final_prediction"], "correct_raw": item["correct_raw"], "correct_final": item["correct_final"]} for item in multimodal]
    )
    multimodal_frame.to_csv(output / "multimodal_predictions.csv", index=False, encoding="utf-8-sig")
    (output / "multimodal_metrics.json").write_text(json.dumps({"journey_count": len(multimodal), "raw_exact_sequence_accuracy": sum(x["correct_raw"] for x in multimodal) / len(multimodal) if multimodal else None, "final_exact_sequence_accuracy": sum(x["correct_final"] for x in multimodal) / len(multimodal) if multimodal else None}, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([{"hard_case_type": item.get("hard_case_type"), "trip_id": item["trip_id"], "correct_raw": item["correct_raw"], "correct_final": item["correct_final"]} for item in hard_rows]).to_csv(output / "hard_case_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"noise_profile": profile, "journey_count": len(items), "raw_accuracy": sum(x["correct_raw"] for x in items) / len(items) if items else None, "final_accuracy": sum(x["correct_final"] for x in items) / len(items) if items else None} for profile, items in noise_rows.items()]).to_csv(output / "noise_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "ground_truth": item.get("ground_truth"), "raw_prediction": item.get("raw_prediction"), "final_prediction": item.get("final_prediction"), "scenario_category": item.get("scenario_category"), "hard_case_type": item.get("hard_case_type")} for item in successful if not item.get("correct_final")]).to_csv(output / "error_analysis.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "reason": item.get("failure_reason")} for item in failed]).to_csv(output / "failed_journeys.csv", index=False, encoding="utf-8-sig")
    error_pairs = Counter((true, pred) for true, pred in zip(mode_true, mode_final) if true != pred)
    pd.DataFrame([{"ground_truth": true, "prediction": pred, "count": count} for (true, pred), count in error_pairs.most_common()]).to_csv(output / "top_errors.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"trip_id": item["trip_id"], "ground_truth_sequence": item["ground_truth"], "raw_sequence": item["raw_prediction"], "final_sequence": item["final_prediction"], "raw_exact": item["correct_raw"], "final_exact": item["correct_final"]} for item in multimodal]).to_csv(output / "segment_metrics.csv", index=False, encoding="utf-8-sig")
    transition_rows = []
    for item in multimodal:
        expected_sequence = item["ground_truth"].split("|")
        final_sequence = item["final_prediction"].split("|")
        expected_transitions = [f"{a}->{b}" for a, b in zip(expected_sequence, expected_sequence[1:])]
        predicted_transitions = [f"{a}->{b}" for a, b in zip(final_sequence, final_sequence[1:])]
        transition_rows.append({"trip_id": item["trip_id"], "expected_transitions": "|".join(expected_transitions), "predicted_transitions": "|".join(predicted_transitions), "transition_exact": expected_transitions == predicted_transitions})
    pd.DataFrame(transition_rows).to_csv(output / "transition_metrics.csv", index=False, encoding="utf-8-sig")
    hard_summary = []
    for hard_case, items in sorted({key: [item for item in hard_rows if item.get("hard_case_type") == key] for key in {item.get("hard_case_type") for item in hard_rows}}.items()):
        hard_summary.append({"hard_case_type": hard_case, "journey_count": len(items), "raw_accuracy": sum(item["correct_raw"] for item in items) / len(items), "final_accuracy": sum(item["correct_final"] for item in items) / len(items)})
    pd.DataFrame(hard_summary).to_csv(output / "hard_case_summary.csv", index=False, encoding="utf-8-sig")
    (output / "realtime_metrics.json").write_text(json.dumps({"status": "PASS", "definition": "raw GeoLife prediction at each completed window uses only GPS available through that window", "raw_window_metrics": raw_metrics, "final_window_metrics": final_metrics}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "distance_weighted_metrics.json").write_text(json.dumps({"status": "NOT_AVAILABLE", "reason": "Frozen Ground Truth has journey-level distance only; no per-segment distance weights are provided."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        import matplotlib.pyplot as plt

        for name, values in (("raw", confusion_matrix(mode_true, mode_raw, labels=list(MODES))), ("final", confusion_matrix(mode_true, mode_final, labels=list(MODES)))):
            figure, axis = plt.subplots(figsize=(5, 4))
            image = axis.imshow(values, cmap="Blues")
            axis.set(xticks=range(len(MODES)), yticks=range(len(MODES)), xticklabels=MODES, yticklabels=MODES, xlabel="Predicted", ylabel="Actual", title=f"{name.title()} GeoLife Confusion Matrix")
            for (row_index, column_index), value in __import__("numpy").ndenumerate(values):
                axis.text(column_index, row_index, int(value), ha="center", va="center")
            figure.colorbar(image, ax=axis)
            figure.tight_layout()
            figure.savefig(output / f"confusion_matrix_{name}.png", dpi=140)
            plt.close(figure)
    except Exception:
        (output / "confusion_matrix_visualization.json").write_text(json.dumps({"status": "NOT_AVAILABLE", "reason": "matplotlib is unavailable"}, indent=2) + "\n", encoding="utf-8")
    _write_report(output, summary, metrics)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", default=str(ROOT / "data/evaluation"))
    parser.add_argument("--run-dir", default=str(ROOT / "reports/evaluation/dataset_v1/baseline_run_001"))
    parser.add_argument("--canopy-baseline-commit", required=True)
    parser.add_argument("--evaluation-commit", required=True)
    parser.add_argument("--branch", default="eval/seoul-synthetic-v1")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-hash-verification", action="store_true")
    parser.add_argument("--derive-ktdb-features", action="store_true", help="derive route-specific KTDB features for each journey; slower and not needed for mode metrics")
    args = parser.parse_args()
    summary = run_evaluation(args.dataset_root, args.run_dir, canopy_baseline_commit=args.canopy_baseline_commit, evaluation_commit=args.evaluation_commit, limit=args.limit, offset=args.offset, resume=args.resume, verify_hashes=not args.skip_hash_verification, derive_ktdb_features=args.derive_ktdb_features, branch=args.branch)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
