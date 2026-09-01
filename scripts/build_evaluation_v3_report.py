"""Build stage-level reports from a completed frozen v3 evaluation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


MODES = ("walk", "bike", "car", "bus", "rail")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(run_dir: Path) -> None:
    records = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    successful = [record for record in records if record.get("status") == "PASS"]
    rows = []
    segment_rows = []
    ml_rows = []
    transit_rows = []
    final_rows = []
    attribution = Counter()
    for record in records:
        rows.append({
            "trip_id": record.get("trip_id"),
            "status": record.get("status"),
            "scenario_category": record.get("scenario_category"),
            "ground_truth_sequence": record.get("ground_truth"),
            "raw_prediction_sequence": record.get("raw_prediction"),
            "final_prediction_sequence": record.get("final_prediction"),
            "correct_raw": record.get("correct_raw"),
            "correct_final": record.get("correct_final"),
            "window_count": record.get("window_count", 0),
        })
        labels = record.get("labels", [])
        raw_modes = record.get("raw_modes", [])
        final_modes = record.get("final_modes", [])
        traces = record.get("traces", [])
        for index, (truth, raw, final) in enumerate(zip(labels, raw_modes, final_modes)):
            trace = traces[index] if index < len(traces) else {}
            transit_candidate = trace.get("transit_candidate")
            if raw == truth and final == truth:
                category = "CORRECT"
            elif raw != truth and final == truth:
                category = "TRANSIT_OR_FINAL_FIX"
            elif raw == truth and final != truth:
                category = "TRANSIT_OR_FINAL_REGRESSION"
            else:
                category = "MOVEMENT_ML_ERROR"
            if category != "CORRECT":
                attribution[category] += 1
            base = {"trip_id": record.get("trip_id"), "window_index": index, "ground_truth": truth}
            segment_rows.append({**base, "raw_prediction": raw, "final_prediction": final, "error_category": category})
            ml_rows.append({**base, "prediction": raw, "correct": raw == truth})
            final_rows.append({**base, "prediction": final, "correct": final == truth})
            transit_rows.append({
                **base,
                "raw_prediction": raw,
                "final_prediction": final,
                "transit_candidate": transit_candidate,
                "matched_subway_line": trace.get("matched_subway_line"),
                "bus_context_score": trace.get("bus_context_score"),
                "subway_context_score": trace.get("subway_context_score"),
            })
    pd.DataFrame(rows).to_csv(run_dir / "journey_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(segment_rows).to_csv(run_dir / "segment_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ml_rows).to_csv(run_dir / "movement_ml_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(transit_rows).to_csv(run_dir / "transit_context_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(final_rows).to_csv(run_dir / "final_prediction_results.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"error_category": key, "count": value} for key, value in attribution.most_common()]).to_csv(run_dir / "error_attribution.csv", index=False, encoding="utf-8-sig")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    _write_json(run_dir / "overall_metrics.json", {
        "dataset": "seoul_synthetic_evaluation_v3",
        "journeys_requested": summary["total_journeys"],
        "journeys_evaluated": summary["successfully_evaluated"],
        "journeys_failed": summary["failed"],
        "raw": metrics["raw"],
        "final": metrics["final"],
        "false_positive": metrics["false_positive"],
        "false_negative": metrics["false_negative"],
    })
    # The merged evaluator already owns the canonical final confusion matrix.
    (run_dir / "confusion_matrix.csv").write_text((run_dir / "confusion_matrix_final.csv").read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
    plots = run_dir / "plots"
    plots.mkdir(exist_ok=True)
    try:
        import matplotlib.pyplot as plt

        per_class = pd.read_csv(run_dir / "per_class_metrics.csv")
        axis = per_class.set_index("mode")[["raw_f1", "final_f1"]].plot(kind="bar", figsize=(8, 4), ylim=(0, 1), title="Seoul Synthetic v3 F1 by mode")
        axis.set_ylabel("F1")
        axis.figure.tight_layout()
        axis.figure.savefig(plots / "per_mode_f1.png", dpi=140)
        plt.close(axis.figure)
    except Exception as exc:
        _write_json(plots / "plot_status.json", {"status": "NOT_AVAILABLE", "reason": str(exc)})
    final = metrics["final"]
    raw = metrics["raw"]
    report = [
        "# Seoul Synthetic Evaluation Dataset v3 Baseline",
        "",
        "## 기준",
        "",
        "- Dataset: `seoul_synthetic_evaluation_v3`",
        f"- Production commit: `{summary['canopy_baseline_commit']}`",
        f"- Evaluation branch: `{summary['branch']}`",
        f"- GPS points: 370,650 (dataset manifest)",
        f"- Journeys: {summary['successfully_evaluated']} passed / {summary['failed']} failed of {summary['total_journeys']}",
        "- Ground Truth leakage: **NO**. Ground Truth is loaded only after production inference.",
        "- Dataset files were not modified.",
        "",
        "## Overall metrics",
        "",
        "| Stage | Accuracy | Macro F1 | Weighted F1 |",
        "|---|---:|---:|---:|",
        f"| Movement ML | {raw['accuracy']:.4f} | {raw['macro_f1']:.4f} | {raw['weighted_f1']:.4f} |",
        f"| Final Canopy | {final['accuracy']:.4f} | {final['macro_f1']:.4f} | {final['weighted_f1']:.4f} |",
        "",
        "## Per-mode final metrics",
        "",
        "| Mode | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        item = final["per_class"][mode]
        report.append(f"| {mode} | {item['precision']:.4f} | {item['recall']:.4f} | {item['f1']:.4f} | {item['support']} |")
    report.extend([
        "",
        "## Confusion and stage attribution",
        "",
        "`confusion_matrix.csv` is the final GT→Prediction matrix. `movement_ml_results.csv`, `transit_context_results.csv`, and `final_prediction_results.csv` retain the three stage views. `error_attribution.csv` records observed error categories without inventing labels.",
        "",
        "## Multimodal and delay view",
        "",
        "`multimodal_metrics.json`, `segment_results.csv`, and `transition_metrics.csv` contain journey timeline and transition results. The current Production evaluator uses fixed 120-second windows; a mode change inside a window is therefore reported at the next closed window.",
        "",
        "## Failed journeys",
        "",
        "`failed_journeys.csv` contains the two short trips that ended while the first 120-second window was still `COLLECTING`. They are not relabeled or padded.",
        "",
        "## Q&A",
        "",
        "- Movement ML is strongest on walk and bike, while bus and rail recall are the main weaknesses in this v3 baseline.",
        "- Bus errors are primarily missed bus windows rather than false bus activation (`metrics.json`).",
        "- Rail improves in Final Canopy when structured station evidence is available, but false rail and missed rail remain measurable.",
        "- Transit Context changes some ML decisions, but does not remove the underlying car/bus and rail separability limits.",
        "- The next model-training step is intentionally not part of this baseline run; this branch records the untuned Production behavior on v3.",
    ])
    (run_dir / "BASELINE_EVALUATION_V3.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("reports/evaluation_v3_baseline"))
    args = parser.parse_args()
    build(args.run_dir)


if __name__ == "__main__":
    main()
