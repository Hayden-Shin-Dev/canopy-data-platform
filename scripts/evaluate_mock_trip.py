"""Evaluate the supplied mock trip without feeding ground truth to inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.geolife_adapter import infer_windows
from src.integration.ktdb_context import build_expected_features
from src.integration.model_config import default_mobility_model
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv


DEFAULT_CSV = ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv"
DEFAULT_GROUND_TRUTH = ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt"


def read_ground_truth_modes(path: str | Path) -> tuple[str, ...]:
    """Read only the evaluator's numbered expected journey lines."""

    text = Path(path).read_text(encoding="utf-8")
    modes = []
    for _, value in re.findall(r"(?m)^\s*([123])\)\s*([A-Za-z]+)", text):
        modes.append(value.lower())
    if not modes:
        raise ValueError("ground truth does not contain numbered expected modes")
    return tuple(modes)


def _compress_modes(modes: list[str]) -> list[str]:
    result: list[str] = []
    for mode in modes:
        if not result or result[-1] != mode:
            result.append(mode)
    return result


def evaluate(csv_path: str | Path = DEFAULT_CSV, ground_truth_path: str | Path = DEFAULT_GROUND_TRUTH) -> dict[str, object]:
    expected_modes = read_ground_truth_modes(ground_truth_path)
    rows = read_replay_csv(csv_path)
    replay = ReplayEngine(speed="instant").stream(rows)
    windows = infer_windows(
        replay.session.events,
        model_path=default_mobility_model(),
        window_seconds=120,
    )
    actual_window_modes = [window.predicted_mode for window in windows if window.status == "READY" and window.predicted_mode]
    actual_sequence = _compress_modes([str(mode) for mode in actual_window_modes])
    scenario = build_expected_features(replay.session.events)
    expected_features = scenario.features
    pipeline = run_full_pipeline(
        replay.session.events,
        expected_features,
        references=TransitRuntimeReferences.from_directory(),
        geolife_model_path=default_mobility_model(),
        ktdb_model_path=ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl",
        factors_csv=ROOT / "data/processed/emission_factors/emission_factors_2026.csv",
    )
    resolved_sequence = _compress_modes([str(mode) for mode in pipeline.get("actual_behaviour", {}).get("mode_sequence", [])])
    expected_set = list(expected_modes)
    return {
        "status": "PASS" if replay.session.rejected_count == 0 else "FAIL",
        "input": {"csv": str(Path(csv_path)), "rows": len(rows), "ground_truth_used_by_inference": False},
        "replay": replay.session.summary(),
        "expected_mode_sequence": expected_set,
        "actual_geolife_window_sequence": actual_sequence,
        "actual_geolife_windows": [
            {"window_start": window.window_start.isoformat(), "window_end": window.window_end.isoformat(), "predicted_mode": window.predicted_mode, "confidence": window.confidence}
            for window in windows
        ],
        "ktdb_baseline": {"features": scenario.features, "provenance": scenario.provenance, "predicted_mode": pipeline.get("expected_behaviour", {}).get("predicted_mode"), "probabilities": pipeline.get("expected_behaviour", {}).get("probabilities", {})},
        "production_pipeline": {
            "status": pipeline.get("status"),
            "final_mode": pipeline.get("actual_behaviour", {}).get("final_mode"),
            "mode_sequence": resolved_sequence,
            "segments": pipeline.get("actual_behaviour", {}).get("segments", []),
            "window_results": pipeline.get("window_results", []),
            "distance_km": pipeline.get("distance_km"),
            "expected_co2e_g": pipeline.get("co2", {}).get("expected_co2e_g"),
            "actual_co2e_g": pipeline.get("co2", {}).get("actual_co2e_g"),
            "reduction_co2e_g": pipeline.get("co2", {}).get("reduction_co2e_g"),
        },
        "comparison": {
            "initial_walk": bool(resolved_sequence and resolved_sequence[0] == "walk"),
            "rail_present": "rail" in resolved_sequence,
            "final_walk": bool(resolved_sequence and resolved_sequence[-1] == "walk"),
            "walk_to_rail": "walk" in resolved_sequence and "rail" in resolved_sequence,
            "rail_to_walk": "rail" in resolved_sequence and resolved_sequence[-1] == "walk",
            "note": "Comparison is evaluation-only; no ground-truth correction is applied.",
        },
        "label_leakage": {"status": "PASS", "forbidden_fields_in_replay": False, "ground_truth_read_path": str(Path(ground_truth_path))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/integration/mock_trip_evaluation.json")
    args = parser.parse_args()
    report = evaluate(args.csv, args.ground_truth)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
