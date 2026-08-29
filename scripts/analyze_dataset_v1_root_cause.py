"""Create diagnostic reports from an already completed blind evaluation run."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.root_cause import (
    MODES,
    correctness_transitions,
    first_error_stage,
    hybrid_interventions,
    multimodal_failures,
    per_mode_correctness,
    raw_final_transition_matrix,
    representative_failures,
    scenario_metrics,
    transit_error_counts,
)


def _load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _transit_evidence(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for journey in predictions:
        for trace in journey.get("traces", []):
            bus = float(trace.get("bus_context_score") or 0.0)
            rail = float(trace.get("subway_context_score") or 0.0)
            if max(bus, rail) >= 0.55:
                level = "strong"
            elif max(bus, rail) >= 0.25:
                level = "weak"
            else:
                level = "none"
            evidence = "bus" if bus >= 0.55 else "rail" if rail >= 0.55 else "other"
            counts[(level, evidence)] += 1
    return [{"evidence_level": level, "evidence_type": kind, "window_count": count}
            for (level, kind), count in sorted(counts.items())]


def _mode_regression(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = per_mode_correctness(predictions)
    rows = []
    for mode in MODES:
        counts = grouped[mode]
        rows.append({
            "ground_truth_mode": mode,
            "kept_correct": counts["kept_correct"],
            "fixed_by_final": counts["fixed_by_final"],
            "broken_by_final": counts["broken_by_final"],
            "still_wrong": counts["still_wrong"],
            "net_correction": counts["fixed_by_final"] - counts["broken_by_final"],
        })
    return rows


def _stage_rows(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for journey in predictions:
        labels = journey.get("labels") or []
        final = journey.get("final_modes") or []
        stage = first_error_stage(journey)
        for truth, prediction in zip(labels, final):
            if truth != prediction:
                counts[(stage, truth)] += 1
    total = sum(counts.values())
    rows = []
    for (stage, mode), count in counts.most_common():
        rows.append({"root_cause": stage, "affected_mode": mode, "count": count,
                     "share": count / total if total else 0.0})
    return rows


def _journey_scope_metrics(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for journey in predictions:
        scope = "multimodal" if len(set(journey.get("labels") or [])) > 1 else "single_mode"
        groups[scope].append(journey)
    return [{
        "scope": scope,
        "journey_count": len(rows),
        "raw_journey_accuracy": sum(bool(row.get("correct_raw")) for row in rows) / len(rows),
        "final_journey_accuracy": sum(bool(row.get("correct_final")) for row in rows) / len(rows),
    } for scope, rows in sorted(groups.items())]


def _first_stage_rows(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(first_error_stage(journey) for journey in predictions)
    total = len(predictions) or 1
    return [{"stage": stage, "journey_count": count, "share": count / total}
            for stage, count in counts.most_common()]


def _markdown(
    summary: dict[str, Any],
    metrics: dict[str, Any],
    transitions: Counter[str],
    interventions: Counter[str],
    mode_rows: list[dict[str, Any]],
    scenario_rows: list[dict[str, Any]],
    multimodal_rows: list[dict[str, Any]],
    hard_rows: list[dict[str, Any]],
    pareto_rows: list[dict[str, Any]],
    scope_rows: list[dict[str, Any]],
) -> str:
    total = sum(transitions.values()) or 1
    lines = [
        "# dataset_v1 Root Cause Analysis",
        "",
        "이 문서는 완료된 blind baseline 결과를 사후 분석한 Evaluation 전용 문서입니다.",
        "Production Prediction Logic, dataset_v1, Ground Truth 정의는 변경하지 않았습니다.",
        "",
        "## Baseline 확인",
        "",
        f"- Canopy Baseline Commit: `{summary.get('canopy_baseline_commit')}`",
        f"- Evaluation Branch: `{summary.get('branch')}`",
        f"- Dataset: `{summary.get('dataset_root')}`",
        f"- Journeys: {summary.get('successfully_evaluated', 0)} / {summary.get('total_journeys', 0)} 성공",
        "- Ground Truth inference leakage: NO",
        "- GPS label leakage: NONE",
        "",
        "## 핵심 결론",
        "",
        "Raw GeoLife와 Final Canopy를 동일한 Ground Truth window 기준으로 비교했습니다.",
        "Hybrid 단계가 전체 성능을 높였는지는 아래 전환 수치와 원인별 집계로 판단합니다.",
        "Ground Truth는 Production inference가 반환된 뒤 평가 단계에서만 읽었습니다.",
        "",
        "## Correctness transition",
        "",
        "| Category | Count | Percentage |",
        "|---|---:|---:|",
    ]
    labels = {
        "KEPT_CORRECT": "Kept Correct", "FIXED_BY_FINAL": "Fixed by Final",
        "BROKEN_BY_FINAL": "Broken by Final", "STILL_WRONG": "Still Wrong",
    }
    for key in ("KEPT_CORRECT", "FIXED_BY_FINAL", "BROKEN_BY_FINAL", "STILL_WRONG"):
        count = transitions[key]
        lines.append(f"| {labels[key]} | {count} | {count / total:.4f} |")
    lines.extend([
        "", f"Net Correction: **{interventions['helpful'] - interventions['harmful']}**",
        f"Helpful Intervention Rate: {interventions['helpful'] / (interventions['total'] or 1):.4f}",
        f"Harmful Intervention Rate: {interventions['harmful'] / (interventions['total'] or 1):.4f}",
        "",
        "## Mode regression",
        "",
        "| Mode | Kept | Fixed | Broken | Still wrong | Net |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in mode_rows:
        lines.append(f"| {row['ground_truth_mode']} | {row['kept_correct']} | {row['fixed_by_final']} | {row['broken_by_final']} | {row['still_wrong']} | {row['net_correction']} |")
    lines.extend(["", "## Mode metrics snapshot", "", "| Mode | Raw F1 | Final F1 |", "|---|---:|---:|"])
    for mode in MODES:
        raw_f1 = metrics.get("raw", {}).get("per_class", {}).get(mode, {}).get("f1", 0.0)
        final_f1 = metrics.get("final", {}).get("per_class", {}).get(mode, {}).get("f1", 0.0)
        lines.append(f"| {mode} | {raw_f1:.4f} | {final_f1:.4f} |")
    lines.extend(["", "## Scenario별 성능", "", "| Scenario | Windows | Raw accuracy | Final accuracy | Difference |", "|---|---:|---:|---:|---:|"])
    for row in scenario_rows:
        lines.append(f"| {row['scenario']} | {row['window_count']} | {row['raw_accuracy']:.4f} | {row['final_accuracy']:.4f} | {row['difference']:.4f} |")
    lines.extend(["", "## Single-mode vs multimodal", "", "| Scope | Journeys | Raw journey accuracy | Final journey accuracy |", "|---|---:|---:|---:|"])
    for row in scope_rows:
        lines.append(f"| {row['scope']} | {row['journey_count']} | {row['raw_journey_accuracy']:.4f} | {row['final_journey_accuracy']:.4f} |")
    lines.extend(["", f"Multimodal journeys: {len(multimodal_rows)}", "- Exact sequence and failure categories are in `multimodal_failure_analysis.csv`.", "- Sequence matching is evaluated without changing the production segmenter.", ""])
    failure_counts = Counter(row["failure_type"] for row in multimodal_rows)
    lines.append("| Failure type | Count |")
    lines.append("|---|---:|")
    for key, count in failure_counts.most_common():
        lines.append(f"| {key} | {count} |")
    lines.extend(["", "## Hard cases", "", "`hard_case_ranking.csv` lists observed hard-case groups and Raw/Final journey accuracy.", ""])
    lines.extend(["## Root cause Pareto", "", "| Rank | Root cause | Mode | Count | Share |", "|---:|---|---|---:|---:|"])
    for index, row in enumerate(pareto_rows, 1):
        lines.append(f"| {index} | {row['root_cause']} | {row['affected_mode']} | {row['count']} | {row['share']:.4f} |")
    lines.extend([
        "", "## Transit / confidence observations", "",
        "Transit evidence levels are descriptive bins over stored trace scores (none < 0.25, weak 0.25–0.55, strong ≥ 0.55); they are not production thresholds.",
        "False activation, missing evidence, and resolver changes are recorded in `transit_error_analysis.csv`.",
        "Raw confidence analysis is NOT_AVAILABLE because the frozen trace stores only the selected raw mode, not class probabilities.",
        "",
        "## Code locations (read-only mapping)",
        "",
        "- Raw ML/window inference: `src/integration/geolife_adapter.py::infer_windows`",
        "- Transit evidence/resolver: `src/integration/pipeline.py::build_transit_context`, `src/transit_context/resolver.py::resolve_mode`",
        "- Smoothing/segmentation: `src/integration/segments.py::smooth_window_modes`, `src/integration/pipeline.py::run_full_pipeline`",
        "- This analysis: `src/evaluation/root_cause.py`, `scripts/analyze_dataset_v1_root_cause.py`",
        "",
        "## Improvement priorities (proposal only)",
        "",
        "- P0: investigate resolver/transit false activations that turn correct walk or bike windows into rail.",
        "- P1: investigate bus evidence coverage and Raw bus recall before changing any resolver behavior.",
        "- P1: improve Raw car/bus/rail class separability with a new independent experiment branch.",
        "- P2: evaluate transition timing and segmentation errors after P0/P1 changes.",
        "",
        "No production change is made by this report. Any improvement must be evaluated in a separate branch against this frozen baseline.",
    ])
    return "\n".join(lines) + "\n"


def analyze(run_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = _load(run_dir / "predictions.jsonl")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))

    matrix = raw_final_transition_matrix(predictions)
    _write_csv(output_dir / "raw_to_final_transition_matrix.csv",
               [{"raw_mode": raw, **matrix[raw]} for raw in MODES], ["raw_mode", *MODES])
    transitions = correctness_transitions(predictions)
    _write_csv(output_dir / "correctness_transitions.csv",
               [{"category": key, "count": transitions[key], "percentage": transitions[key] / (sum(transitions.values()) or 1)} for key in ("KEPT_CORRECT", "FIXED_BY_FINAL", "BROKEN_BY_FINAL", "STILL_WRONG")],
               ["category", "count", "percentage"])
    mode_rows = _mode_regression(predictions)
    _write_csv(output_dir / "mode_regression_analysis.csv", mode_rows, list(mode_rows[0]))
    intervention = hybrid_interventions(predictions)
    _write_json(output_dir / "hybrid_interventions.json", dict(intervention))
    _write_csv(output_dir / "hybrid_interventions.csv",
               [{"category": key, "count": value} for key, value in intervention.items()], ["category", "count"])
    transit = transit_error_counts(predictions)
    _write_csv(output_dir / "transit_error_analysis.csv",
               [{"metric": key, "count": value} for key, value in sorted(transit.items())], ["metric", "count"])
    _write_csv(output_dir / "transit_evidence_levels.csv", _transit_evidence(predictions), ["evidence_level", "evidence_type", "window_count"])
    multimodal_rows = multimodal_failures(predictions)
    _write_csv(output_dir / "multimodal_failure_analysis.csv", multimodal_rows,
               ["trip_id", "ground_truth_sequence", "raw_sequence", "final_sequence", "failure_type"])
    scenario_rows = scenario_metrics(predictions)
    _write_csv(output_dir / "scenario_analysis.csv", scenario_rows, list(scenario_rows[0]) if scenario_rows else ["scenario"])
    hard_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for journey in predictions:
        raw_key = journey.get("hard_case_type")
        key = "none" if raw_key is None or str(raw_key).lower() in {"", "nan", "none"} else str(raw_key)
        hard_groups[key].append(journey)
    hard_rows = []
    for key, rows in sorted(hard_groups.items()):
        hard_rows.append({"hard_case_type": key, "journey_count": len(rows),
                          "raw_accuracy": sum(bool(row.get("correct_raw")) for row in rows) / len(rows),
                          "final_accuracy": sum(bool(row.get("correct_final")) for row in rows) / len(rows)})
    _write_csv(output_dir / "hard_case_ranking.csv", hard_rows, list(hard_rows[0]))
    pareto_rows = _stage_rows(predictions)
    _write_csv(output_dir / "root_cause_pareto.csv", pareto_rows, ["root_cause", "affected_mode", "count", "share"])
    _write_json(output_dir / "representative_failures.json", representative_failures(predictions))
    _write_json(output_dir / "raw_final_transition_summary.json", {"matrix": matrix, "interventions": dict(intervention), "transit": dict(transit)})
    _write_csv(output_dir / "single_vs_multimodal.csv", _journey_scope_metrics(predictions),
               ["scope", "journey_count", "raw_journey_accuracy", "final_journey_accuracy"])
    _write_csv(output_dir / "first_error_stage.csv", _first_stage_rows(predictions), ["stage", "journey_count", "share"])
    _write_json(output_dir / "confidence_analysis.json", {
        "status": "NOT_AVAILABLE",
        "reason": "prediction_traces.jsonl stores selected raw_mode but not raw class probabilities/confidence.",
        "required_for": ["high-confidence raw correctness", "confidence vs resolver override"],
    })
    (output_dir / "improvement_priorities.md").write_text(
        "# Improvement priorities\n\n"
        "이 파일은 진단 결과에 따른 제안만 담으며 Production 코드를 변경하지 않습니다.\n\n"
        "## P0\n\n"
        "- walk/bike/car를 rail로 바꾸는 false transit activation을 trace 단위로 재현하고 resolver 입력을 점검합니다.\n\n"
        "## P1\n\n"
        "- bus evidence coverage와 Raw bus recall을 먼저 보강합니다.\n"
        "- car/bus/rail 분리를 위한 독립 실험을 별도 branch에서 수행합니다.\n\n"
        "## P2\n\n"
        "- transition timing과 segmentation 개선을 ablation으로 검증합니다.\n",
        encoding="utf-8",
    )
    _write_json(output_dir / "analysis_manifest.json", {
        "input_run": str(run_dir),
        "output_dir": str(output_dir),
        "production_logic_modified": False,
        "dataset_modified": False,
        "ground_truth_used_only_after_inference": True,
        "confidence_analysis": "NOT_AVAILABLE",
        "distance_weighted_metrics": "NOT_AVAILABLE",
    })
    scope_rows = _journey_scope_metrics(predictions)
    (output_dir / "ROOT_CAUSE_ANALYSIS.md").write_text(
        _markdown(summary, metrics, transitions, intervention, mode_rows, scenario_rows, multimodal_rows, hard_rows, pareto_rows, scope_rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("reports/evaluation/dataset_v1/baseline_run_001"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/evaluation/dataset_v1/root_cause_analysis_001"))
    args = parser.parse_args()
    analyze(args.run_dir, args.output_dir)


if __name__ == "__main__":
    main()
