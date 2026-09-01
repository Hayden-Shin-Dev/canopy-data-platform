"""서울 라벨 fixture에서 GeoLife raw와 Transit fusion을 비교한다."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.replay_integration import _load_expected_features
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from src.integration.geolife_adapter import infer_windows
from src.integration.model_config import default_mobility_model


LABELS = {
    "seoul_bus_route.csv": "bus",
    "seoul_car_no_transit.csv": "car",
    "seoul_subway_line1.csv": "rail",
    "seoul_walk_bike.csv": "walk",
}
CLASSES = ("walk", "bike", "car", "bus", "rail")


def _majority(values: list[str]) -> str | None:
    return Counter(values).most_common(1)[0][0] if values else None


def evaluate(fixture_dir: str | Path, output: str | Path) -> dict[str, object]:
    root = Path(fixture_dir)
    references = TransitRuntimeReferences.from_directory()
    rows: list[dict[str, object]] = []
    for filename, expected in LABELS.items():
        fixture = root / filename
        events = ReplayEngine(speed="instant").stream(read_replay_csv(fixture)).session.events
        expected_features = _load_expected_features(None, fixture=fixture, events=events)
        windows = infer_windows(events, model_path=default_mobility_model(), window_seconds=120)
        ready = [window for window in windows if window.status == "READY"]
        raw = _majority([str(window.predicted_mode) for window in ready if window.predicted_mode])
        pipeline = run_full_pipeline(
            events,
            expected_features,
            references=references,
            geolife_model_path=default_mobility_model(),
            ktdb_model_path=Path("models/expected_behaviour/ktdb_population_baseline.pkl"),
            factors_csv=Path("data/processed/emission_factors/emission_factors_2026.csv"),
        )
        fused = _majority([str(mode) for mode in pipeline.get("actual_behaviour", {}).get("mode_sequence", [])])
        rows.append({"fixture": filename, "expected": expected, "raw_mode": raw, "fused_mode": fused, "raw_correct": raw == expected, "fused_correct": fused == expected})
    result = {
        "label_source": "fixture metadata in data/fixtures/integration/README.md; labels are not passed to inference",
        "rows": rows,
        "raw_accuracy": sum(row["raw_correct"] for row in rows) / len(rows),
        "fused_accuracy": sum(row["fused_correct"] for row in rows) / len(rows),
        "false_rail_raw": sum(row["raw_mode"] == "rail" and row["expected"] != "rail" for row in rows),
        "false_rail_fused": sum(row["fused_mode"] == "rail" and row["expected"] != "rail" for row in rows),
        "class_support": {label: sum(row["expected"] == label for row in rows) for label in CLASSES},
        "note": "The supplied labelled fixtures contain no bike-labelled trajectory; bike precision/recall is NOT TESTED rather than inferred.",
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=Path("data/fixtures/integration"))
    parser.add_argument("--output", type=Path, default=Path("reports/integration/runs/transit_fusion_evaluation.json"))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.fixture_dir, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
