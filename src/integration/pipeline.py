"""End-to-end integration orchestration using existing production components."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.config import PROJECT_ROOT
from src.transit_context.evidence import bus_context, korail_context, subway_context
from src.transit_context.references import normalize_korail_stations, normalize_subway_stations, normalize_subway_timetable
from src.transit_context.resolver import resolve_mode
from src.transit_context.spatial import GeoPointIndex

from .distance import trajectory_distance_km
from .emissions import calculate_actual_emission, calculate_expected_emission, load_factor_resolver
from .expected_behaviour import ExpectedBehaviourResult, predict_expected
from .geolife_adapter import WindowInference, build_window_event_table, infer_windows
from .gps_contract import GpsEvent


@dataclass(frozen=True)
class TransitRuntimeReferences:
    bus_stops: pd.DataFrame
    bus_route_stops: pd.DataFrame
    bus_stop_index: GeoPointIndex
    subway_stations: pd.DataFrame
    subway_index: GeoPointIndex
    korail_stations: pd.DataFrame
    korail_index: GeoPointIndex
    subway_timetable: pd.DataFrame | None = None

    @classmethod
    def from_directory(cls, reference_dir: str | Path | None = None) -> "TransitRuntimeReferences":
        directory = Path(reference_dir) if reference_dir is not None else PROJECT_ROOT / "data/processed/transit_context"
        paths = {
            "bus_stops": directory / "seoul_bus_stops.csv",
            "bus_route_stops": directory / "seoul_bus_route_stops.csv",
            "subway_stations": directory / "subway_stations.csv",
            "korail_stations": directory / "korail_stations.csv",
            "subway_timetable": directory / "subway_timetable.csv",
        }
        missing = [str(path) for key, path in paths.items() if key != "subway_timetable" and not path.is_file()]
        if missing:
            raise FileNotFoundError(f"transit reference files not found: {missing}")
        bus_stops = pd.read_csv(paths["bus_stops"])
        bus_route_stops = pd.read_csv(paths["bus_route_stops"])
        subway_stations = pd.read_csv(paths["subway_stations"])
        korail_stations = pd.read_csv(paths["korail_stations"])
        timetable = pd.read_csv(paths["subway_timetable"]) if paths["subway_timetable"].is_file() else None
        return cls(
            bus_stops=bus_stops,
            bus_route_stops=bus_route_stops,
            bus_stop_index=GeoPointIndex.from_frame(bus_stops),
            subway_stations=subway_stations,
            subway_index=GeoPointIndex.from_frame(subway_stations),
            korail_stations=korail_stations,
            korail_index=GeoPointIndex.from_frame(korail_stations),
            subway_timetable=timetable,
        )


def _observed_bus_stops(events: Sequence[GpsEvent], references: TransitRuntimeReferences) -> list[str]:
    radius = 300.0
    observed: list[str] = []
    for event in events:
        nearest = references.bus_stop_index.nearest(event.latitude, event.longitude)
        if float(nearest["distance_m"]) <= radius:
            stop_id = str(nearest["stop_id"])
            if not observed or observed[-1] != stop_id:
                observed.append(stop_id)
    return observed


def build_transit_context(events: Sequence[GpsEvent], probabilities: dict[str, float], references: TransitRuntimeReferences) -> dict[str, object]:
    if len(events) < 2:
        return {"bus_context_score": 0.0, "subway_context_score": 0.0, "train_context_score": 0.0, "context_status": "INSUFFICIENT_GPS"}
    start, end = events[0], events[-1]
    bus = bus_context(
        start_latitude=start.latitude,
        start_longitude=start.longitude,
        end_latitude=end.latitude,
        end_longitude=end.longitude,
        bus_stop_index=references.bus_stop_index,
        bus_stops=references.bus_stops,
        bus_route_stops=references.bus_route_stops,
        observed_stop_ids=_observed_bus_stops(events, references),
    )
    subway = subway_context(
        start_latitude=start.latitude,
        start_longitude=start.longitude,
        end_latitude=end.latitude,
        end_longitude=end.longitude,
        station_index=references.subway_index,
        stations=references.subway_stations,
        ml_rail_probability=probabilities.get("rail", 0.0),
    )
    korail = korail_context(
        start_latitude=start.latitude,
        start_longitude=start.longitude,
        end_latitude=end.latitude,
        end_longitude=end.longitude,
        station_index=references.korail_index,
        ml_rail_probability=probabilities.get("rail", 0.0),
    )
    return {**bus, **subway, **korail, "context_status": "READY"}


def _mode_segments(timeline: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Collapse adjacent ready windows into auditable trip mode segments."""

    segments: list[dict[str, object]] = []
    for item in timeline:
        if item.get("status") != "READY" or not item.get("final_mode"):
            continue
        mode = str(item["final_mode"])
        if segments and segments[-1]["mode"] == mode:
            segments[-1]["window_end"] = item["window_end"]
            segments[-1]["window_count"] = int(segments[-1]["window_count"]) + 1
            segments[-1]["point_count"] = int(segments[-1]["point_count"]) + int(item["point_count"])
            segments[-1]["distance_km"] = float(segments[-1]["distance_km"]) + float(item["distance_km"])
        else:
            segments.append(
                {
                    "mode": mode,
                    "window_start": item["window_start"],
                    "window_end": item["window_end"],
                    "window_count": 1,
                    "point_count": int(item["point_count"]),
                    "distance_km": float(item["distance_km"]),
                }
            )
    return segments


def run_full_pipeline(
    events: Sequence[GpsEvent],
    expected_features: dict[str, object],
    *,
    references: TransitRuntimeReferences,
    geolife_model_path: str | Path,
    ktdb_model_path: str | Path,
    factors_csv: str | Path,
    window_seconds: int = 120,
) -> dict[str, object]:
    """Run one stopped trip through ML, transit context, expected behaviour and CO2."""

    if len(events) < 2:
        return {"status": "COLLECTING", "reason": "at least two accepted GPS events are required"}
    windows: list[WindowInference] = infer_windows(events, model_path=geolife_model_path, window_seconds=window_seconds)
    ready = [window for window in windows if window.status == "READY"]
    if not ready:
        return {"status": "COLLECTING", "windows": [window.__dict__ for window in windows]}
    event_table = build_window_event_table(events, window_seconds=window_seconds)
    timeline: list[dict[str, object]] = []
    for index, (inference, table_item) in enumerate(zip(windows, event_table, strict=True)):
        _, window_events, _ = table_item
        if inference.status != "READY":
            timeline.append(
                {
                    "window_index": index,
                    "window_start": inference.window_start.isoformat(),
                    "window_end": inference.window_end.isoformat(),
                    "status": inference.status,
                    "point_count": len(window_events),
                }
            )
            continue
        context = build_transit_context(window_events, inference.probabilities, references)
        decision = resolve_mode(inference.probabilities, context=context)
        timeline.append(
            {
                "window_index": index,
                "window_start": inference.window_start.isoformat(),
                "window_end": inference.window_end.isoformat(),
                "status": inference.status,
                "point_count": len(window_events),
                "distance_km": trajectory_distance_km(window_events) if len(window_events) >= 2 else 0.0,
                "probabilities": inference.probabilities,
                "predicted_mode": inference.predicted_mode,
                "confidence": inference.confidence,
                "transit_context": context,
                "final_mode": decision["final_mode"],
                "decision_status": decision["decision_status"],
                "correction_applied": decision["correction_applied"],
            }
        )
    latest = ready[-1]
    latest_item = next(item for item in reversed(timeline) if item.get("status") == "READY")
    ml_probabilities = latest.probabilities
    transit = build_transit_context(events, ml_probabilities, references)
    decision = resolve_mode(ml_probabilities, context=transit)
    expected: ExpectedBehaviourResult = predict_expected(expected_features, model_path=ktdb_model_path)
    resolver = load_factor_resolver(factors_csv)
    distance_km = trajectory_distance_km(events)
    segments = _mode_segments(timeline)
    segment_emissions = [
        calculate_actual_emission(str(segment["mode"]), float(segment["distance_km"]), resolver=resolver)
        for segment in segments
        if float(segment["distance_km"]) > 0
    ]
    actual_co2 = sum(float(item["co2e_g"]) for item in segment_emissions)
    actual = {
        "mode": decision["final_mode"],
        "distance_km": distance_km,
        "co2e_g": actual_co2,
        "resolved_factor": segment_emissions[-1]["resolved_factor"] if segment_emissions else resolver.resolve_emission_factor(str(decision["final_mode"])),
        "segments": segment_emissions,
    }
    expected_emission = calculate_expected_emission(expected.probabilities, distance_km, resolver=resolver)
    reduction = float(expected_emission["expected_co2e_g"]) - float(actual["co2e_g"])
    return {
        "status": "PASS",
        "distance_km": distance_km,
        "accepted_event_count": len(events),
        "window": {**latest.features, "status": latest.status, "probabilities": latest.probabilities, "predicted_mode": latest.predicted_mode, "confidence": latest.confidence, "final_mode": latest_item["final_mode"]},
        "prediction_timeline": timeline,
        "mode_segments": segments,
        "mode_transitions": [
            {"from": previous["mode"], "to": current["mode"], "at": current["window_start"]}
            for previous, current in zip(segments, segments[1:])
        ],
        "transit_context": transit,
        "actual_behaviour": {**decision, "emission": actual},
        "expected_behaviour": {"probabilities": expected.probabilities, "predicted_mode": expected.predicted_mode, "emission": expected_emission},
        "co2": {"expected_co2e_g": expected_emission["expected_co2e_g"], "actual_co2e_g": actual["co2e_g"], "reduction_co2e_g": reduction, "increase": reduction < 0},
    }
