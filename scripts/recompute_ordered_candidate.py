"""Recompute ordered-bus candidate metrics from an existing blind run."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.evaluate_dataset_v1 import _metric_payload

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preserve-rail", action="store_true")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    y_true, y_raw, y_final = [], [], []
    for row in rows:
        labels, raw, final = row.get("labels", []), row.get("raw_modes", []), row.get("final_modes", [])
        adjusted = [
            "bus" if raw_mode == "bus" else "rail" if args.preserve_rail and raw_mode == "rail" else predicted
            for raw_mode, predicted in zip(raw, final)
        ]
        y_true.extend(labels); y_raw.extend(raw); y_final.extend(adjusted)
    payload = {"raw": _metric_payload(y_true, y_raw), "final": _metric_payload(y_true, y_final), "false_bus": {"total": sum(a != "bus" and b == "bus" for a, b in zip(y_true, y_final)), "walk": sum(a == "walk" and b == "bus" for a, b in zip(y_true, y_final)), "bike": sum(a == "bike" and b == "bus" for a, b in zip(y_true, y_final)), "car": sum(a == "car" and b == "bus" for a, b in zip(y_true, y_final)), "rail": sum(a == "rail" and b == "bus" for a, b in zip(y_true, y_final))}, "false_rail": sum(a != "rail" and b == "rail" for a, b in zip(y_true, y_final)), "count": len(rows), "windows": len(y_true), "ground_truth_used_in_inference": False}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
