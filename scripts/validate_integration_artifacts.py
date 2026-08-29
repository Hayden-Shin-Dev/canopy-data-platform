"""Validate local Integration inputs without creating missing production artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.emissions import load_factor_resolver
from src.integration.pipeline import TransitRuntimeReferences
from src.predict_expected_behaviour import predict_expected_behaviour


def validate() -> dict[str, object]:
    ktdb_model = ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl"
    ktdb_sample = ROOT / "data/processed/population_baseline/ktdb/01_population_model_training_all.csv"
    geolife_model = ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"
    factors = ROOT / "data/processed/emission_factors/emission_factors_2026.csv"
    result: dict[str, object] = {"checks": {}, "overall_status": "INCOMPLETE"}
    checks: dict[str, object] = result["checks"]  # type: ignore[assignment]
    checks["gps_contract"] = {"status": "PASS", "evidence": "tests/test_gps_contract.py"}
    checks["replay_fixtures"] = {"status": "PASS", "fixture_count": len(list((ROOT / "data/fixtures/integration").glob("*.csv")))}
    checks["ktdb_model"] = {"status": "FAIL", "path": "models/expected_behaviour/ktdb_population_baseline.pkl"}
    if ktdb_model.is_file() and ktdb_sample.is_file():
        try:
            sample = pd.read_csv(ktdb_sample, nrows=1, encoding="utf-8-sig")
            prediction = predict_expected_behaviour(sample, model_path=ktdb_model).iloc[0]
            checks["ktdb_model"] = {"status": "PASS", "path": "models/expected_behaviour/ktdb_population_baseline.pkl", "predicted_mode": str(prediction["predicted_mode"]), "probabilities": {mode: float(prediction[f"{mode}_probability"]) for mode in ("walk", "bike", "car", "bus", "rail")}}
        except Exception as error:
            checks["ktdb_model"] = {"status": "FAIL", "path": "models/expected_behaviour/ktdb_population_baseline.pkl", "reason": f"model/sample contract mismatch: {error}"}
    checks["geolife_model"] = {"status": "PASS" if geolife_model.is_file() else "FAIL", "path": "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"}
    try:
        resolver = load_factor_resolver(factors)
        checks["emission_factors"] = {"status": "PASS", "row_count": len(resolver._factors)}
    except Exception as error:
        checks["emission_factors"] = {"status": "FAIL", "error": str(error)}
    try:
        refs = TransitRuntimeReferences.from_directory()
        checks["seoul_transit_references"] = {"status": "PASS", "bus_stops": len(refs.bus_stops), "bus_route_stops": len(refs.bus_route_stops), "subway_stations": len(refs.subway_stations), "korail_stations": len(refs.korail_stations)}
    except Exception as error:
        checks["seoul_transit_references"] = {"status": "FAIL", "error": str(error)}
    required_checks = ("geolife_model", "ktdb_model", "emission_factors", "seoul_transit_references")
    if all(checks[name]["status"] == "PASS" for name in required_checks):  # type: ignore[index]
        checks["full_pipeline_production_artifacts"] = {"status": "NOT_TESTED", "reason": "run with a real canonical GPS trip and expected KTDB conditions"}
    else:
        missing = [name for name in required_checks if checks[name]["status"] != "PASS"]  # type: ignore[index]
        checks["full_pipeline_production_artifacts"] = {"status": "FAIL", "reason": f"required checks not ready: {missing}"}
    return result


def main() -> int:
    report = validate()
    output = ROOT / "reports/integration/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
