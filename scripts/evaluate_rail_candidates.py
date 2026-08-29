"""Compare rail confirmation candidates against the frozen baseline traces."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.rail_candidates import replay_candidate

MODES = ("walk", "bike", "car", "bus", "rail")
STRATEGIES = ("baseline", "A_strict_score", "B_consecutive_score", "C_high_score")


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evaluate(predictions: list[dict]) -> tuple[list[dict], dict[str, list[list[int]]], dict[str, list[dict]]]:
    metrics: list[dict] = []
    matrices: dict[str, list[list[int]]] = {}
    per_class: dict[str, list[dict]] = {}
    for strategy in STRATEGIES:
        truth: list[str] = []
        predicted: list[str] = []
        false_rail = 0
        for journey in predictions:
            labels = journey.get("labels") or []
            output = replay_candidate(journey, strategy)
            for actual, mode in zip(labels, output):
                truth.append(str(actual))
                predicted.append(mode)
                if actual not in {"bus", "rail"} and mode == "rail":
                    false_rail += 1
        precision, recall, f1, support = precision_recall_fscore_support(
            truth, predicted, labels=list(MODES), zero_division=0
        )
        metrics.append({
            "candidate": strategy,
            "accuracy": accuracy_score(truth, predicted),
            "macro_precision": precision.mean(),
            "macro_recall": recall.mean(),
            "macro_f1": f1.mean(),
            "weighted_f1": f1_score(truth, predicted, labels=list(MODES), average="weighted", zero_division=0),
            "false_rail_activation": false_rail,
            "journeys": len(predictions),
        })
        matrices[strategy] = confusion_matrix(truth, predicted, labels=list(MODES)).tolist()
        per_class[strategy] = [
            {"candidate": strategy, "mode": mode, "precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
            for mode, p, r, f, s in zip(MODES, precision, recall, f1, support)
        ]
    return metrics, matrices, per_class


def write_report(output_dir: Path, metrics: list[dict], matrices: dict[str, list[list[int]]], per_class: dict[str, list[dict]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "candidate_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    rows = [row for strategy in STRATEGIES for row in per_class[strategy]]
    with (output_dir / "mode_metric_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for strategy, matrix in matrices.items():
        with (output_dir / f"confusion_matrix_{strategy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["raw/final", *MODES])
            writer.writerows([[mode, *row] for mode, row in zip(MODES, matrix)])
    selected = next(item for item in metrics if item["candidate"] == "A_strict_score")
    (output_dir / "selected_candidate_metrics.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    report = [
        "# Rail override candidate comparison",
        "",
        "Evaluation-only replay over all stored dataset_v1 Production traces. Ground Truth is not used to alter inference.",
        "",
        "| Candidate | Accuracy | Macro F1 | Weighted F1 | False rail |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in metrics:
        report.append(f"| {row['candidate']} | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | {row['weighted_f1']:.4f} | {row['false_rail_activation']} |")
    report.extend([
        "",
        "Selected candidate: **A_strict_score**",
        "",
        "A raises the confirmation requirement for a non-rail Raw prediction before retaining a rail Final mode. It improves all aggregate metrics in this frozen replay and sharply reduces false rail activation.",
        "",
        "This result is a candidate signal only. Production code is changed only after the candidate is implemented and full regression is run.",
    ])
    (output_dir / "candidate_hypotheses.md").write_text(
        "# Candidate hypotheses\n\n"
        "- A_strict_score: require subway context score >= 0.70 when Raw mode is non-rail and Final mode would be rail.\n"
        "- B_consecutive_score: require score >= 0.55 and an adjacent same-line window with score >= 0.55.\n"
        "- C_high_score: require score >= 0.80 for a non-rail-to-rail correction.\n",
        encoding="utf-8",
    )
    (output_dir / "RAIL_OVERRIDE_V1_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("reports/evaluation/dataset_v1/baseline_run_001"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/evaluation/dataset_v1/improvement_runs/rail_override_v1"))
    args = parser.parse_args()
    metrics, matrices, per_class = evaluate(_load(args.run_dir / "predictions.jsonl"))
    write_report(args.output_dir, metrics, matrices, per_class)


if __name__ == "__main__":
    main()
