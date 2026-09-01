"""Replay selected AI-Hub Test trajectories through the production pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.aihub.replay import iter_aihub_payloads, load_split_manifest, validate_replay_uid
from src.integration.geolife_adapter import infer_windows
from src.integration.ktdb_context import build_expected_features
from src.integration.model_config import default_mobility_model
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine


def _load_manifest(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def replay_entry(
    entry: dict[str, object],
    *,
    source_root: str | Path,
    speed: int | str = "instant",
    references: TransitRuntimeReferences | None = None,
) -> dict[str, object]:
    """Run one manifest entry; ground truth is read only after inference returns."""

    split_path = ROOT / "data/interim/aihub/aihub_split_manifest.json"
    split_map = load_split_manifest(split_path)
    validate_replay_uid(str(entry["uid"]), split_map)
    payloads = list(iter_aihub_payloads(entry, source_root=source_root))
    replay = ReplayEngine(speed=speed).stream(payloads)
    events = replay.session.events
    model = default_mobility_model()
    windows = infer_windows(events, model_path=model, window_seconds=120)
    ground_truth = str(entry["ground_truth"])
    movement_modes = [window.predicted_mode for window in windows if window.status == "READY" and window.predicted_mode]
    result: dict[str, object] = {
        "replay_id": entry["replay_id"],
        "uid": entry["uid"],
        "trajectory_id": entry["trajectory_id"],
        "ground_truth": ground_truth,
        "point_count": len(events),
        "duration_seconds": (events[-1].timestamp - events[0].timestamp).total_seconds() if events else 0,
        "replay_status": replay.status,
        "movement_prediction": movement_modes[-1] if movement_modes else None,
        "movement_probabilities": windows[-1].probabilities if windows else {},
        "temporal_prediction": [],
        "transit_context_result": [],
        "final_prediction": None,
        "movement_correct": movement_modes[-1] == ground_truth if movement_modes else False,
        "final_correct": False,
        "pipeline_status": "NOT_RUN",
        "distance_km": None,
        "emission": {},
    }
    try:
        expected = build_expected_features(events)
        pipeline = run_full_pipeline(
            events,
            expected.features,
            references=references or TransitRuntimeReferences.from_directory(),
            geolife_model_path=model,
            ktdb_model_path=ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl",
            factors_csv=ROOT / "data/processed/emission_factors/emission_factors_2026.csv",
        )
    except Exception as error:
        result["pipeline_status"] = "KTDB_CONTEXT_UNAVAILABLE"
        result["error"] = str(error)
        return result
    final_mode = pipeline.get("actual_behaviour", {}).get("final_mode")
    result.update(
        {
            "temporal_prediction": pipeline.get("actual_behaviour", {}).get("mode_sequence", []),
            "transit_context_result": pipeline.get("window_results", []),
            "final_prediction": final_mode,
            "final_correct": final_mode == ground_truth,
            "pipeline_status": pipeline.get("status"),
            "distance_km": pipeline.get("distance_km"),
            "emission": pipeline.get("co2", {}),
        }
    )
    return result


def replay_batch(manifest_path: str | Path, *, source_root: str | Path, speed: int | str = "instant") -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    references = TransitRuntimeReferences.from_directory()
    results = [replay_entry(entry, source_root=source_root, speed=speed, references=references) for entry in manifest["trajectories"]]
    return {
        "manifest": str(Path(manifest_path)),
        "model": str(default_mobility_model()),
        "speed": speed,
        "trajectory_count": len(results),
        "movement_correct_count": sum(bool(row["movement_correct"]) for row in results),
        "final_correct_count": sum(bool(row["final_correct"]) for row in results),
        "pipeline_status_counts": {
            status: sum(row["pipeline_status"] == status for row in results)
            for status in sorted({str(row["pipeline_status"]) for row in results})
        },
        "by_class": {
            mode: {
                "count": sum(row["ground_truth"] == mode for row in results),
                "movement_correct": sum(bool(row["movement_correct"]) for row in results if row["ground_truth"] == mode),
                "final_correct": sum(bool(row["final_correct"]) for row in results if row["ground_truth"] == mode),
            }
            for mode in ("walk", "bike", "car", "bus", "rail")
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root")
    parser.add_argument("--manifest", default="data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json")
    parser.add_argument("--replay-id")
    parser.add_argument("--speed", default="instant", choices=("instant", "1", "5", "10", "30"))
    parser.add_argument("--output", default="reports/aihub/AIHUB_REPLAY_RESULTS.json")
    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)
    if args.replay_id:
        entries = [entry for entry in manifest["trajectories"] if entry["replay_id"] == args.replay_id]
        if not entries:
            raise SystemExit(f"unknown replay id: {args.replay_id}")
        output = replay_entry(entries[0], source_root=args.source_root, speed=args.speed)
    else:
        output = replay_batch(args.manifest, source_root=args.source_root, speed=args.speed)
    destination = ROOT / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
