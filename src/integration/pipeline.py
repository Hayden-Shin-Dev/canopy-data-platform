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
from src.emission_factors.calculator import calculate_multimodal_trip
from src.transit_context.settings import load_settings

from .emissions import calculate_expected_emission, load_factor_resolver
from .expected_behaviour import ExpectedBehaviourResult, predict_expected
from .geolife_adapter import WindowInference, infer_windows
from .gps_contract import GpsEvent
from .segments import smooth_window_modes


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


def build_transit_context(
    events: Sequence[GpsEvent],
    probabilities: dict[str, float],
    references: TransitRuntimeReferences,
    *,
    station_history: Sequence[tuple[str, str]] = (),
) -> dict[str, object]:
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
        trajectory=[(event.latitude, event.longitude) for event in events],
        station_history=station_history,
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
    first_timestamp = events[0].timestamp
    station_history: list[tuple[str, str]] = []
    window_records: list[dict[str, object]] = []
    for index, window in enumerate(ready):
        window_events = [
            event for event in events
            if window.window_start <= event.timestamp < window.window_end
            or (index == len(ready) - 1 and event.timestamp == window.window_end)
        ]
        transit = build_transit_context(window_events, window.probabilities, references, station_history=station_history)
        decision = resolve_mode(window.probabilities, context=transit)
        window_records.append({
            "index": index,
            "window": window,
            "events": window_events,
            "transit_context": transit,
            "decision": decision,
        })
        current_ids = transit.get("subway_current_observed_station_ids", [])
        current_line = transit.get("matched_subway_line")
        if current_line is not None:
            for station_id in current_ids:
                item = (str(station_id), str(current_line))
                if item not in station_history:
                    station_history.append(item)
    settings = load_settings()
    smoothed_modes = smooth_window_modes(
        window_records,
        minimum_context_score=settings.resolver["minimum_context_score"],
        minimum_ml_confidence=settings.resolver["minimum_ml_confidence"],
    )
    for record, mode in zip(window_records, smoothed_modes):
        decision = dict(record["decision"])
        if mode != decision["final_mode"]:
            decision["final_mode"] = mode
            decision["correction_applied"] = True
            decision["decision_status"] = "smoothed"
            decision["correction_reason"] = "continued ordered transit evidence across adjacent windows"
            decision["rail_subtype"] = "subway" if mode == "rail" else None
        record["decision"] = decision
    latest_record = window_records[-1]
    latest = latest_record["window"]
    transit = latest_record["transit_context"]
    decision = latest_record["decision"]
    expected: ExpectedBehaviourResult = predict_expected(expected_features, model_path=ktdb_model_path)
    resolver = load_factor_resolver(factors_csv)
    distance_km = trajectory_distance_km(events)
    segments: list[dict[str, object]] = []
    start = 0
    for segment_index, mode in enumerate(smoothed_modes):
        if segment_index < len(smoothed_modes) - 1 and mode == smoothed_modes[segment_index + 1]:
            continue
        segment_start = start
        segment_end = segment_index
        segment_windows = window_records[segment_start:segment_end + 1]
        segment_events = [event for record in segment_windows for event in record["events"]]
        deduped_events = list(dict.fromkeys(segment_events))
        if deduped_events:
            segment_distance = trajectory_distance_km(deduped_events)
            segment_start_time = deduped_events[0].timestamp
            segment_end_time = deduped_events[-1].timestamp
            start_coordinate = [deduped_events[0].latitude, deduped_events[0].longitude]
            end_coordinate = [deduped_events[-1].latitude, deduped_events[-1].longitude]
        else:
            segment_distance = 0.0
            segment_start_time = segment_windows[0]["window"].window_start
            segment_end_time = segment_windows[-1]["window"].window_end
            start_coordinate = None
            end_coordinate = None
        factor = resolver.resolve_emission_factor(mode)
        segments.append({
            "mode": mode,
            "start_time": segment_start_time.isoformat(),
            "end_time": segment_end_time.isoformat(),
            "duration_sec": max(0.0, (segment_end_time - segment_start_time).total_seconds()),
            "distance_km": segment_distance,
            "start_coordinate": start_coordinate,
            "end_coordinate": end_coordinate,
            "window_indices": [int(record["index"]) for record in segment_windows],
            "window_count": len(segment_windows),
            "transit_evidence": [record["transit_context"] for record in segment_windows],
            "matched_subway_line": next((record["transit_context"].get("matched_subway_line") for record in reversed(segment_windows) if record["transit_context"].get("matched_subway_line")), None),
            "resolved_factor": factor,
        })
        start = segment_index + 1
    actual = calculate_multimodal_trip(segments)
    expected_emission = calculate_expected_emission(expected.probabilities, distance_km, resolver=resolver)
    reduction = float(expected_emission["expected_co2e_g"]) - float(actual["trip_total_co2e_g"])
    for item, emission in zip(segments, actual["segments"]):
        item.update({key: emission[key] for key in ("subtype", "factor", "unit", "co2e_g", "fallback_used")})
        item.pop("resolved_factor", None)
    window_results = []
    for record, mode in zip(window_records, smoothed_modes):
        window = record["window"]
        window_results.append({
            "window_start": window.window_start.isoformat(),
            "window_end": window.window_end.isoformat(),
            "features": window.features,
            "probabilities": window.probabilities,
            "geolife_predicted_mode": window.predicted_mode,
            "final_mode": mode,
            "decision": record["decision"],
            "transit_context": record["transit_context"],
        })
    return {
        "status": "PASS",
        "distance_km": distance_km,
        "accepted_event_count": len(events),
        "window": {**latest.features, "status": latest.status, "probabilities": latest.probabilities, "predicted_mode": latest.predicted_mode, "confidence": latest.confidence, "final_mode": decision["final_mode"]},
        "window_results": window_results,
        "transit_context": transit,
        "actual_behaviour": {**decision, "mode_sequence": smoothed_modes, "segments": segments, "emission": actual},
        "expected_behaviour": {"probabilities": expected.probabilities, "predicted_mode": expected.predicted_mode, "emission": expected_emission},
        "co2": {"expected_co2e_g": expected_emission["expected_co2e_g"], "actual_co2e_g": actual["trip_total_co2e_g"], "reduction_co2e_g": reduction, "increase": reduction < 0},
    }
