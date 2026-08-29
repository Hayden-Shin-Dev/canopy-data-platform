"""Replay a canonical GPS fixture event-by-event and optionally run the pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from src.ktdb.schema import MODEL_FEATURES


DEFAULT_MOCK = ROOT / "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv"
DEFAULT_KTDB_SAMPLE = ROOT / "data/processed/population_baseline/ktdb/01_population_model_training_all.csv"


def _load_expected_features(path: Path | None) -> dict[str, object]:
    """Load existing KTDB feature values for local replay; do not invent labels."""

    if path is not None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("KTDB feature input must be a JSON object")
        return payload
    if not DEFAULT_KTDB_SAMPLE.is_file():
        raise FileNotFoundError(
            "KTDB sample is required for --pipeline; provide --ktdb-features"
        )
    sample = pd.read_csv(DEFAULT_KTDB_SAMPLE, nrows=1, encoding="utf-8-sig").iloc[0]
    return {name: sample[name] for name in MODEL_FEATURES}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, nargs="?", default=DEFAULT_MOCK)
    parser.add_argument("--speed", choices=("1", "5", "10", "30", "instant"), default="instant")
    parser.add_argument("--pipeline", action="store_true", help="run model/transit/emission integration after replay")
    parser.add_argument("--geolife-model", type=Path, default=ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib")
    parser.add_argument("--ktdb-model", type=Path, default=ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl")
    parser.add_argument("--factors", type=Path, default=ROOT / "data/processed/emission_factors/emission_factors_2026.csv")
    parser.add_argument("--ktdb-features", type=Path, help="developer-only JSON with the existing KTDB feature contract")
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
            expected_features = _load_expected_features(args.ktdb_features)
            pipeline = run_full_pipeline(result.session.events, expected_features, references=references, geolife_model_path=args.geolife_model, ktdb_model_path=args.ktdb_model, factors_csv=args.factors)
        except Exception as error:  # CLI reports an explicit FAIL instead of hiding unavailable local artifacts.
            pipeline = {"status": "FAIL", "error": str(error)}
        payload["pipeline"] = pipeline
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
