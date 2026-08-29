"""Replay a canonical GPS fixture event-by-event and optionally run the pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from src.ktdb.schema import MODEL_FEATURES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--speed", choices=("1", "5", "10", "30", "instant"), default="instant")
    parser.add_argument("--pipeline", action="store_true", help="run model/transit/emission integration after replay")
    parser.add_argument("--geolife-model", type=Path, default=ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib")
    parser.add_argument("--ktdb-model", type=Path, default=ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl")
    parser.add_argument("--factors", type=Path, default=ROOT / "data/processed/emission_factors/emission_factors_2026.csv")
    args = parser.parse_args()

    rows = read_replay_csv(args.fixture)
    engine = ReplayEngine(speed=args.speed if args.speed == "instant" else int(args.speed))
    result = engine.stream(rows)
    payload: dict[str, object] = {
        "replay_status": result.status,
        "session": result.session.summary(),
        "updates": [
            {"index": update.index, "accepted": update.decision.accepted, "reasons": update.decision.reasons, "warnings": update.decision.warnings}
            for update in result.updates
        ],
    }
    if args.pipeline:
        try:
            references = TransitRuntimeReferences.from_directory()
            expected_features = {name: "<required-input>" for name in MODEL_FEATURES}
            pipeline = run_full_pipeline(result.session.events, expected_features, references=references, geolife_model_path=args.geolife_model, ktdb_model_path=args.ktdb_model, factors_csv=args.factors)
        except Exception as error:  # CLI reports an explicit FAIL instead of hiding unavailable local artifacts.
            pipeline = {"status": "FAIL", "error": str(error)}
        payload["pipeline"] = pipeline
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
