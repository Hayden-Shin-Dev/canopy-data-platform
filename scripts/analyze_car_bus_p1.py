"""Analyze Car/Bus errors without changing Production inference."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODES = ("walk", "bike", "car", "bus", "rail")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def confusion(predictions: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    matrix = Counter()
    values_key = "raw_modes" if field == "raw" else "final_modes"
    for journey in predictions:
        for truth, prediction in zip(journey.get("labels") or [], journey.get(values_key) or []):
            matrix[(str(truth), str(prediction))] += 1
    return [{"ground_truth": truth, "prediction": prediction, "count": matrix[(truth, prediction)]} for truth in MODES for prediction in MODES]


def correctness_for_mode(predictions: list[dict[str, Any]], mode: str) -> dict[str, int]:
    result = Counter()
    for journey in predictions:
        for truth, raw, final in zip(journey.get("labels") or [], journey.get("raw_modes") or [], journey.get("final_modes") or []):
            if truth != mode:
                continue
            if raw == mode and final == mode:
                result["kept_correct"] += 1
            elif raw != mode and final == mode:
                result["fixed_by_final"] += 1
            elif raw == mode and final != mode:
                result["broken_by_final"] += 1
            else:
                result["still_wrong"] += 1
    return {key: result.get(key, 0) for key in ("kept_correct", "fixed_by_final", "broken_by_final", "still_wrong")}


def bus_evidence(predictions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bins = Counter()
    final_not_bus = Counter()
    for journey in predictions:
        for truth, final, trace in zip(journey.get("labels") or [], journey.get("final_modes") or [], journey.get("traces") or []):
            if truth != "bus":
                continue
            score = float(trace.get("bus_context_score") or 0.0)
            level = "none" if score < 0.25 else "weak" if score < 0.55 else "strong"
            bins[level] += 1
            if final != "bus":
                final_not_bus[final] += 1
    total = sum(bins.values()) or 1
    coverage = [{"evidence_level": key, "window_count": bins[key], "share_of_bus_windows": bins[key] / total} for key in ("none", "weak", "strong")]
    return coverage, [{"final_mode": key, "count": value} for key, value in sorted(final_not_bus.items())]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def gps_trip_features(gps_path: Path) -> dict[str, float]:
    rows = []
    with gps_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                rows.append((float(row["latitude"]), float(row["longitude"]), max(0.0, float(row.get("speed_mps") or 0.0)), row["timestamp"]))
            except (KeyError, TypeError, ValueError):
                continue
    if len(rows) < 2:
        return {}
    distances = [_haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(rows, rows[1:])]
    intervals = []
    for a, b in zip(rows, rows[1:]):
        try:
            from datetime import datetime
            intervals.append(max(0.001, (datetime.fromisoformat(b[3].replace("Z", "+00:00")) - datetime.fromisoformat(a[3].replace("Z", "+00:00"))).total_seconds()))
        except ValueError:
            intervals.append(1.0)
    speeds = [row[2] for row in rows]
    accelerations = [(b - a) / dt for a, b, dt in zip(speeds, speeds[1:], intervals)]
    distance = sum(distances)
    displacement = _haversine_m(rows[0][0], rows[0][1], rows[-1][0], rows[-1][1])
    return {
        "mean_speed_mps": statistics.mean(speeds),
        "max_speed_mps": max(speeds),
        "speed_std_mps": statistics.pstdev(speeds) if len(speeds) > 1 else 0.0,
        "stop_ratio": sum(speed < 0.5 for speed in speeds) / len(speeds),
        "mean_abs_acceleration_mps2": statistics.mean(abs(value) for value in accelerations) if accelerations else 0.0,
        "distance_m": distance,
        "displacement_m": displacement,
        "straightness_ratio": displacement / distance if distance else 0.0,
        "avg_sampling_interval_sec": statistics.mean(intervals) if intervals else 0.0,
    }


def feature_overlap(dataset_root: Path, manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in manifest:
        mode = str(row.get("scenario_category", ""))
        if mode in {"car", "bus"}:
            features = gps_trip_features(dataset_root / "gps" / f"{row['trip_id']}.csv")
            if features:
                grouped[mode].append(features)
    names = ["mean_speed_mps", "max_speed_mps", "speed_std_mps", "stop_ratio", "mean_abs_acceleration_mps2", "distance_m", "displacement_m", "straightness_ratio", "avg_sampling_interval_sec"]
    output = []
    for name in names:
        car = [item[name] for item in grouped["car"]]
        bus = [item[name] for item in grouped["bus"]]
        low = max(min(car, default=0.0), min(bus, default=0.0))
        high = min(max(car, default=0.0), max(bus, default=0.0))
        denominator = max(max(car, default=0.0) - min(car, default=0.0), max(bus, default=0.0) - min(bus, default=0.0), 1e-9)
        output.append({"feature": name, "car_count": len(car), "car_mean": statistics.mean(car) if car else 0.0, "car_median": statistics.median(car) if car else 0.0, "bus_count": len(bus), "bus_mean": statistics.mean(bus) if bus else 0.0, "bus_median": statistics.median(bus) if bus else 0.0, "range_overlap_ratio": max(0.0, high - low) / denominator})
    return output


def failure_pareto(predictions: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    counts = Counter()
    for journey in predictions:
        for truth, raw, final in zip(journey.get("labels") or [], journey.get("raw_modes") or [], journey.get("final_modes") or []):
            if truth != mode or final == mode:
                continue
            if raw == mode and final in {"rail", "bus"}:
                cause = "transit_override_after_raw_correct"
            elif mode == "bus" and raw == "car":
                cause = "raw_predicts_car"
            elif mode == "car" and raw == "bus":
                cause = "raw_predicts_bus"
            elif raw in {"walk", "bike"}:
                cause = "raw_predicts_walk_or_bike"
            else:
                cause = "other_raw_confusion"
            counts[cause] += 1
    total = sum(counts.values()) or 1
    return [{"cause": cause, "count": count, "share": count / total} for cause, count in counts.most_common()]


def analyze(run_dir: Path, dataset_root: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = load_jsonl(run_dir / "predictions.jsonl")
    baseline_predictions = load_jsonl(Path("reports/evaluation/dataset_v1/baseline_run_001/predictions.jsonl"))
    with (dataset_root / "journey_manifest.csv").open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    write_csv(output_dir / "raw_car_bus_confusion.csv", [row for row in confusion(baseline_predictions, "raw") if row["ground_truth"] in {"car", "bus"}], ["ground_truth", "prediction", "count"])
    write_csv(output_dir / "final_car_bus_confusion.csv", [row for row in confusion(predictions, "final") if row["ground_truth"] in {"car", "bus"}], ["ground_truth", "prediction", "count"])
    transition_rows = []
    for mode in ("car", "bus"):
        values = correctness_for_mode(predictions, mode)
        transition_rows.append({"mode": mode, **values, "net_correction": values.get("fixed_by_final", 0) - values.get("broken_by_final", 0)})
    write_csv(output_dir / "car_bus_correctness_transition.csv", transition_rows, ["mode", "kept_correct", "fixed_by_final", "broken_by_final", "still_wrong", "net_correction"])
    coverage, not_bus = bus_evidence(predictions)
    write_csv(output_dir / "bus_evidence_coverage.csv", coverage, ["evidence_level", "window_count", "share_of_bus_windows"])
    write_csv(output_dir / "bus_evidence_but_final_not_bus.csv", not_bus, ["final_mode", "count"])
    write_csv(output_dir / "bus_failure_pareto.csv", failure_pareto(predictions, "bus"), ["cause", "count", "share"])
    write_csv(output_dir / "car_failure_pareto.csv", failure_pareto(predictions, "car"), ["cause", "count", "share"])
    overlap = feature_overlap(dataset_root, manifest)
    write_csv(output_dir / "car_bus_feature_overlap.csv", overlap, list(overlap[0]))
    for mode in ("car", "bus"):
        failures = []
        for journey in predictions:
            if journey.get("ground_truth") != mode or journey.get("correct_final"):
                continue
            failures.append({"trip_id": journey.get("trip_id"), "ground_truth": mode, "raw_prediction": journey.get("raw_prediction"), "final_prediction": journey.get("final_prediction"), "window_count": journey.get("window_count")})
        (output_dir / f"representative_{mode}_failures.json").write_text(json.dumps(failures[:25], ensure_ascii=False, indent=2), encoding="utf-8")
    # Multimodal journeys carry per-window labels, so count labels rather than
    # relying on the journey-level ground_truth field.
    bus_gt = sum(sum(label == "bus" for label in (j.get("labels") or [])) for j in predictions)
    evidence_present = sum(row["window_count"] for row in coverage if row["evidence_level"] in {"weak", "strong"})
    false_bus_by_truth = Counter()
    car_evidence_groups = Counter()
    for journey in predictions:
        for truth, final, trace in zip(journey.get("labels") or [], journey.get("final_modes") or [], journey.get("traces") or []):
            if final == "bus" and truth != "bus":
                false_bus_by_truth[str(truth)] += 1
            if truth == "car":
                score = float(trace.get("bus_context_score") or 0.0)
                car_evidence_groups["bus_evidence" if score >= 0.25 else "none"] += 1
    summary = {
        "dataset": "dataset_v1",
        "journeys": len(predictions),
        "bus_ground_truth_windows": bus_gt,
        "bus_evidence_present_proxy_windows": evidence_present,
        "bus_evidence_proxy_recall": evidence_present / bus_gt if bus_gt else 0.0,
        "bus_evidence_definition": "stored bus_context_score >= 0.25; component-level evidence is not persisted in trace",
        "false_bus_activation_by_ground_truth": dict(false_bus_by_truth),
        "car_evidence_groups": dict(car_evidence_groups),
        "production_logic_modified": False,
        "ground_truth_used_to_infer": False,
    }
    (output_dir / "p1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("reports/evaluation/dataset_v1/improvement_runs/rail_override_v1/full_run"))
    parser.add_argument("--dataset-root", type=Path, default=Path("data/evaluation/seoul-synthetic/evaluation_dataset_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/evaluation/dataset_v1/p1_car_bus_analysis_001"))
    args = parser.parse_args()
    analyze(args.run_dir, args.dataset_root, args.output_dir)


if __name__ == "__main__":
    main()
