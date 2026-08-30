"""Summarize stateful bus evidence from a frozen evaluation run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def analyze(run_dir: Path, output_dir: Path) -> None:
    records = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    states = Counter()
    telemetry_present = 0
    state_gt = defaultdict(Counter)
    transitions = Counter()
    delays: list[int] = []
    release_delays: list[int] = []
    for record in records:
        previous = "UNKNOWN"
        bus_start = None
        for index, trace in enumerate(record.get("traces", [])):
            if "bus_state" in trace:
                telemetry_present += 1
            state = str(trace.get("bus_state") or "UNKNOWN") if "bus_state" in trace else "NOT_CAPTURED"
            gt = str(trace.get("ground_truth") or "unknown")
            states[state] += 1
            state_gt[state][gt] += 1
            if state != previous:
                transitions[(previous, state)] += 1
            if state == "BUS_CONFIRMED" and bus_start is None:
                bus_start = index
                if gt == "bus":
                    delays.append(index)
            if previous == "BUS_CONFIRMED" and state != previous and gt != "bus":
                release_delays.append(index)
            previous = state
    state_rows = []
    for state in ("UNKNOWN", "BUS_CANDIDATE", "BUS_PROBABLE", "BUS_CONFIRMED", "NOT_CAPTURED"):
        total = states[state]
        true_bus = state_gt[state]["bus"]
        state_rows.append({
            "state": state,
            "windows": total,
            "gt_bus_windows": true_bus,
            "gt_bus_rate": round(true_bus / total, 6) if total else 0.0,
            "non_bus_windows": total - true_bus,
        })
    _write_rows(output_dir / "bus_state_transition_metrics.csv", ["state", "windows", "gt_bus_windows", "gt_bus_rate", "non_bus_windows"], state_rows)
    _write_rows(
        output_dir / "bus_transition_timing.csv",
        ["metric", "value"],
        [
            {"metric": "confirmed_entries", "value": transitions[("BUS_PROBABLE", "BUS_CONFIRMED")] + transitions[("BUS_CANDIDATE", "BUS_CONFIRMED")] + transitions[("UNKNOWN", "BUS_CONFIRMED")]},
            {"metric": "mean_confirmation_window_index_on_gt_bus", "value": round(sum(delays) / len(delays), 4) if delays else "N/A"},
            {"metric": "mean_release_window_index_after_confirmation", "value": round(sum(release_delays) / len(release_delays), 4) if release_delays else "N/A"},
            {"metric": "state_transitions", "value": sum(transitions.values())},
            {"metric": "state_telemetry_windows", "value": telemetry_present},
        ],
    )
    _write_rows(
        output_dir / "window_evidence_duration_analysis.csv",
        ["state", "transitions_into_state"],
        [{"state": state, "transitions_into_state": sum(count for (before, after), count in transitions.items() if after == state)} for state in ("UNKNOWN", "BUS_CANDIDATE", "BUS_PROBABLE", "BUS_CONFIRMED")],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.run_dir, args.output_dir)


if __name__ == "__main__":
    main()
