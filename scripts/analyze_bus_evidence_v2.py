"""Summarize production Bus Evidence traces without changing inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

MODES = ("walk", "bike", "car", "bus", "rail")


def _read(path: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"trace file is empty: {path}")
    for column in ("nearest_bus_stop_distance_m", "bus_context_score", "route_candidate_count", "progression_length"):
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    for column in ("route_consistent", "ordered_stop_progression", "direction_consistent", "temporal_consistent", "bus_speed_plausible", "bus_evidence_present"):
        frame[column] = frame.get(column, False).fillna(False).astype(bool)
    return frame


def _rate(frame: pd.DataFrame, mask: pd.Series) -> dict[str, float | int]:
    selected = frame[mask]
    bus = frame["ground_truth"].eq("bus")
    return {
        "count": int(mask.sum()),
        "gt_bus_count": int((mask & bus).sum()),
        "gt_bus_rate": float((mask & bus).sum() / bus.sum()) if bus.sum() else 0.0,
        "precision": float((mask & bus).sum() / mask.sum()) if mask.sum() else 0.0,
    }


def analyze(trace_path: Path, output_dir: Path) -> None:
    frame = _read(trace_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    signal_rows = []
    signals = {
        "stop_within_radius": frame["nearest_bus_stop_distance_m"].notna() & frame["nearest_bus_stop_distance_m"].le(150),
        "route_candidate_exists": frame["route_candidate_count"].fillna(0).gt(0),
        "route_consistent": frame["route_consistent"],
        "ordered_stop_progression": frame["ordered_stop_progression"],
        "direction_consistent": frame["direction_consistent"],
        "temporal_consistent": frame["temporal_consistent"],
        "speed_plausible": frame["bus_speed_plausible"],
        "bus_evidence_present": frame["bus_evidence_present"],
    }
    for name, mask in signals.items():
        values = _rate(frame, mask)
        signal_rows.append({"signal": name, **values, "gt_non_bus_activation": int((mask & frame["ground_truth"].ne("bus")).sum())})
    pd.DataFrame(signal_rows).to_csv(output_dir / "evidence_signal_summary.csv", index=False, encoding="utf-8-sig")

    distance_rows = []
    for mode in MODES:
        values = frame.loc[frame["ground_truth"].eq(mode), "nearest_bus_stop_distance_m"].dropna()
        if len(values):
            distance_rows.append({"ground_truth": mode, "count": len(values), "mean_m": values.mean(), "median_m": values.median(), "p25_m": values.quantile(.25), "p75_m": values.quantile(.75), "p90_m": values.quantile(.90), "p95_m": values.quantile(.95)})
    pd.DataFrame(distance_rows).to_csv(output_dir / "stop_distance_distribution.csv", index=False, encoding="utf-8-sig")

    radius_rows = []
    for radius in (50, 75, 100, 125, 150, 200):
        mask = frame["nearest_bus_stop_distance_m"].notna() & frame["nearest_bus_stop_distance_m"].le(radius)
        values = _rate(frame, mask)
        radius_rows.append({"radius_m": radius, **values, "non_bus_activation": int((mask & frame["ground_truth"].ne("bus")).sum())})
    pd.DataFrame(radius_rows).to_csv(output_dir / "radius_sensitivity.csv", index=False, encoding="utf-8-sig")

    contamination = frame.groupby("ground_truth", dropna=False)["route_candidate_count"].agg(["count", "mean", "median", lambda values: values.quantile(.90)]).reset_index()
    contamination.columns = ["ground_truth", "count", "mean_candidates", "median_candidates", "p90_candidates"]
    contamination.to_csv(output_dir / "route_candidate_contamination.csv", index=False, encoding="utf-8-sig")

    false_bus = frame[(frame["final_mode"] == "bus") & (frame["ground_truth"] != "bus")].copy()
    false_bus["reason"] = false_bus.apply(lambda row: "stop_only" if not row["route_consistent"] else "route_without_progression" if not row["ordered_stop_progression"] else "progression", axis=1)
    false_bus.groupby(["ground_truth", "reason"], dropna=False).size().reset_index(name="count").to_csv(output_dir / "false_bus_root_causes.csv", index=False, encoding="utf-8-sig")

    true_bus = frame[frame["ground_truth"] == "bus"].copy()
    pattern_columns = (("stop", "stop_within_radius"), ("route", "route_consistent"), ("progression", "ordered_stop_progression"), ("direction", "direction_consistent"), ("temporal", "temporal_consistent"), ("speed", "speed_plausible"))
    true_bus["pattern"] = [
        "+".join(name for name, key in pattern_columns if bool(signals[key].loc[index]))
        for index in true_bus.index
    ]
    true_bus.groupby("pattern", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False).to_csv(output_dir / "true_bus_evidence_patterns.csv", index=False, encoding="utf-8-sig")

    summary = {
        "trace_rows": int(len(frame)),
        "gt_mode_counts": frame["ground_truth"].value_counts().to_dict(),
        "false_bus_total": int(len(false_bus)),
        "true_bus_windows": int(len(true_bus)),
        "bus_evidence_proxy_precision": float(((frame["bus_evidence_present"]) & frame["ground_truth"].eq("bus")).sum() / frame["bus_evidence_present"].sum()) if frame["bus_evidence_present"].sum() else 0.0,
        "bus_evidence_proxy_recall": float(((frame["bus_evidence_present"]) & frame["ground_truth"].eq("bus")).sum() / len(true_bus)) if len(true_bus) else 0.0,
        "production_logic_changed": False,
        "ground_truth_used_in_inference": False,
    }
    (output_dir / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.traces, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
