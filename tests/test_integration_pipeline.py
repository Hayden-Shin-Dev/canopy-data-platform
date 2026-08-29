from datetime import datetime, timedelta, timezone

import joblib
import pandas as pd

from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.gps_contract import validate_gps_event
from src.ktdb.schema import MODEL_FEATURES
from src.transit_context.spatial import GeoPointIndex


class _StaticGeoModel:
    def predict_proba(self, frame):
        return [[0.05, 0.05, 0.05, 0.8, 0.05] for _ in range(len(frame))]


class _StaticKtdbModel:
    classes_ = ["walk", "bike"]

    def predict_proba(self, frame):
        return [[0.4, 0.6] for _ in range(len(frame))]


def _events():
    start = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    events = []
    for sequence, seconds, longitude in ((0, 0, 126.9780), (1, 60, 126.9790), (2, 119, 126.9800), (3, 120, 126.9810), (4, 180, 126.9820)):
        result = validate_gps_event({
            "schema_version": "1.0", "trip_id": "trip-1", "device_id": "device-1", "sequence": sequence,
            "timestamp": (start + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z"), "latitude": 37.5665,
            "longitude": longitude, "horizontal_accuracy_m": 5, "altitude_m": 30, "vertical_accuracy_m": 5,
            "speed_mps": 2, "course_deg": 90,
        })
        assert result.event is not None
        events.append(result.event)
    return events


def _references():
    bus = pd.DataFrame({"stop_id": ["s1", "s2"], "stop_name": ["A", "B"], "latitude": [37.5665, 37.5665], "longitude": [126.978, 126.982]})
    route = pd.DataFrame({"route_id": ["r1", "r1"], "route_no": ["1", "1"], "stop_id": ["s1", "s2"], "stop_sequence": [1, 2], "latitude": [37.5665, 37.5665], "longitude": [126.978, 126.982]})
    subway = pd.DataFrame({"station_id": ["u1", "u2"], "station_name": ["A", "B"], "line": ["1", "1"], "latitude": [37.0, 38.0], "longitude": [127.0, 128.0]})
    korail = pd.DataFrame({"station_id": ["k1", "k2"], "station_name": ["A", "B"], "latitude": [35.0, 36.0], "longitude": [129.0, 130.0]})
    return TransitRuntimeReferences(bus, route, GeoPointIndex.from_frame(bus), subway, GeoPointIndex.from_frame(subway), korail, GeoPointIndex.from_frame(korail))


def test_full_pipeline_uses_real_adapters_and_preserves_negative_reduction(tmp_path):
    geo_path = tmp_path / "geo.joblib"
    joblib.dump({"model": _StaticGeoModel(), "feature_columns": ["point_count", "observed_duration_sec", "distance_m", "displacement_m", "straightness_ratio", "mean_speed_mps", "max_speed_mps", "speed_std_mps", "mean_abs_acceleration_mps2", "acceleration_std_mps2", "stop_ratio", "mean_heading_change_deg", "altitude_range_m", "avg_sampling_interval_sec", "valid_step_count", "gap_step_count"], "classes": ["walk", "bike", "car", "bus", "rail"]}, geo_path)
    ktdb_path = tmp_path / "ktdb.joblib"
    joblib.dump({"backend": "sklearn", "model": _StaticKtdbModel()}, ktdb_path)
    factors = pd.DataFrame([
        ["walk", "conventional_walk", None, None, 0, "gCO2e/person.km", 2026, "test"],
        ["bike", "conventional_bicycle", None, None, 0, "gCO2e/person.km", 2026, "test"],
        ["car", "unknown_average", "unknown", "average", 180, "gCO2e/vehicle.km", 2026, "test"],
        ["bus", "average_local_bus", None, None, 100, "gCO2e/passenger.km", 2026, "test"],
        ["rail", "national_rail", None, None, 40, "gCO2e/passenger.km", 2026, "test"],
    ], columns=["canonical_mode", "emission_subtype", "fuel_type", "vehicle_size", "factor_value", "normalized_unit", "source_year", "source_name"])
    for column, default in [("source_factor_value", 0), ("source_unit", ""), ("source_category", ""), ("source_activity", ""), ("ghg_boundary", "operational"), ("is_fallback", False), ("source_row_identifier", "id")]:
        factors[column] = default
    factors_path = tmp_path / "factors.csv"
    factors.to_csv(factors_path, index=False)

    result = run_full_pipeline(_events(), {name: "x" for name in MODEL_FEATURES}, references=_references(), geolife_model_path=geo_path, ktdb_model_path=ktdb_path, factors_csv=factors_path)

    assert result["status"] == "PASS"
    assert result["actual_behaviour"]["final_mode"] == "bus"
    assert "increase" in result["co2"]
