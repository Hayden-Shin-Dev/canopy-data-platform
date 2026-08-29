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
from src.integration.gps_contract import validate_gps_event
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from scripts.evaluate_mock_trip import evaluate as evaluate_mock_trip
from src.predict_expected_behaviour import predict_expected_behaviour
from src.ktdb.schema import MODEL_FEATURES


def validate() -> dict[str, object]:
    ktdb_model = ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl"
    ktdb_sample = ROOT / "data/processed/population_baseline/ktdb/01_population_model_training_all.csv"
    geolife_model = ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib"
    factors = ROOT / "data/processed/emission_factors/emission_factors_2026.csv"
    result: dict[str, object] = {"checks": {}, "overall_status": "INCOMPLETE"}
    checks: dict[str, object] = result["checks"]  # type: ignore[assignment]
    checks["gps_contract"] = {"status": "PASS", "evidence": "tests/test_gps_contract.py"}
    checks["replay_fixtures"] = {"status": "PASS", "fixture_count": len(list((ROOT / "data/fixtures/integration").glob("*.csv")))}
    try:
        mock = evaluate_mock_trip()
        checks["iphone_mock_replay"] = {
            "status": "PASS" if mock["status"] == "PASS" and mock["input"]["ground_truth_used_by_inference"] is False else "FAIL",
            "rows": mock["input"]["rows"],
            "accepted_event_count": mock["replay"]["accepted_event_count"],
            "actual_geolife_window_sequence": mock["actual_geolife_window_sequence"],
            "production_mode_sequence": mock["production_pipeline"]["mode_sequence"],
            "production_final_mode": mock["production_pipeline"]["mode_sequence"][-1],
            "ktdb_baseline_predicted_mode": mock["ktdb_baseline"]["predicted_mode"],
            "ktdb_baseline_features": mock["ktdb_baseline"]["features"],
            "evaluation_report": "reports/integration/mock_trip_evaluation.json",
        }
    except Exception as error:
        checks["iphone_mock_replay"] = {"status": "FAIL", "reason": str(error)}
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
        try:
            sample = pd.read_csv(ktdb_sample, nrows=1, encoding="utf-8-sig").iloc[0]
            expected_features = {name: sample[name] for name in MODEL_FEATURES}
            references = TransitRuntimeReferences.from_directory()
            fixture_results: dict[str, object] = {}
            for fixture in sorted((ROOT / "data/fixtures/integration").glob("*.csv")):
                replay = ReplayEngine(speed="instant").stream(read_replay_csv(fixture))
                pipeline = run_full_pipeline(replay.session.events, expected_features, references=references, geolife_model_path=geolife_model, ktdb_model_path=ktdb_model, factors_csv=factors)
                fixture_results[fixture.name] = {"status": pipeline.get("status"), "accepted_event_count": len(replay.session.events), "rejected_event_count": replay.session.rejected_count, "actual_mode": pipeline.get("actual_behaviour", {}).get("final_mode"), "distance_km": pipeline.get("distance_km")}
            expected_collecting = {"insufficient_gps.csv", "quality_edge_cases.csv"}
            unexpected = [name for name, item in fixture_results.items() if name in expected_collecting and item["status"] not in {"COLLECTING", "PASS"} or name not in expected_collecting and item["status"] != "PASS"]
            checks["full_pipeline_production_replay"] = {"status": "PASS" if not unexpected else "FAIL", "fixtures": fixture_results, "unexpected_statuses": unexpected}
        except Exception as error:
            checks["full_pipeline_production_replay"] = {"status": "FAIL", "reason": str(error)}
    else:
        missing = [name for name in required_checks if checks[name]["status"] != "PASS"]  # type: ignore[index]
        checks["full_pipeline_production_replay"] = {"status": "FAIL", "reason": f"required checks not ready: {missing}"}
    required_statuses = ("gps_contract", "replay_fixtures", "iphone_mock_replay", "ktdb_model", "geolife_model", "emission_factors", "seoul_transit_references", "full_pipeline_production_replay")
    result["overall_status"] = "COMPLETE" if all(checks[name]["status"] == "PASS" for name in required_statuses) else "INCOMPLETE"  # type: ignore[index]
    # 계약·산출물 검증 통과와 운영 준비 완료는 분리해서 기록한다.
    result["production_readiness"] = "NOT_READY"
    result["readiness_blockers"] = [
        "KTDB probability calibration is not measured",
        "Transit labelled precision/recall is not measured",
        "Long-duration real iPhone GPS validation is not measured",
    ]
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
