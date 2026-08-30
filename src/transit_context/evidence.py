"""Evidence scores for transit context; these functions do not train a model."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import pandas as pd

from .settings import TransitSettings, load_settings
from .spatial import GeoPointIndex


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    available = [(key, _bounded(value)) for key, value in values.items() if key in weights]
    total = sum(weights[key] for key, _ in available)
    return _bounded(sum(weights[key] * value for key, value in available) / total) if total else 0.0


def sequence_score(observed_stop_ids: Sequence[str], route_stops: pd.DataFrame) -> float:
    """Score monotonic forward or reverse movement through one ordered route."""

    if len(observed_stop_ids) < 2 or route_stops.empty:
        return 0.0
    required = {"stop_id", "stop_sequence"}
    if not required <= set(route_stops.columns):
        raise ValueError(f"노선 순서 계산에 필요한 컬럼이 없습니다: {sorted(required - set(route_stops.columns))}")
    sequence_frame = route_stops.drop_duplicates("stop_id").copy()
    sequence = dict(zip(sequence_frame["stop_id"].astype(str), sequence_frame["stop_sequence"], strict=False))
    values = [float(sequence[str(stop)]) for stop in observed_stop_ids if str(stop) in sequence]
    if len(values) < 2:
        return 0.0
    adjacent = [b - a for a, b in zip(values, values[1:]) if b != a]
    if not adjacent:
        return 0.0
    forward = sum(delta > 0 for delta in adjacent) / len(adjacent)
    reverse = sum(delta < 0 for delta in adjacent) / len(adjacent)
    return _bounded(max(forward, reverse))


def bus_context(
    *,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    bus_stop_index: GeoPointIndex | None,
    bus_stops: pd.DataFrame | None,
    bus_route_stops: pd.DataFrame | None,
    observed_stop_ids: Sequence[str] = (),
    trajectory: Sequence[tuple[float, float]] = (),
    timestamps: Sequence[object] = (),
    live_match_score: float = 0.0,
    settings: TransitSettings | None = None,
) -> dict[str, object]:
    settings = settings or load_settings()
    empty = {
        "nearby_bus_stop_count": 0,
        "matched_bus_route_id": None,
        "matched_bus_route_no": None,
        "matched_bus_stop_count": 0,
        "bus_stop_proximity_score": 0.0,
        "bus_route_match_score": 0.0,
        "bus_sequence_score": 0.0,
        "live_bus_match_score": _bounded(live_match_score),
        "bus_context_score": 0.0,
        "bus_evidence_reason": "bus reference unavailable",
        "nearest_bus_stop_id": None,
        "nearest_bus_stop_distance_m": None,
        "matched_stop_ids": [],
        "route_candidate_ids": [],
        "route_candidate_count": 0,
        "route_consistent": False,
        "route_consistency_count": 0,
        "ordered_stop_progression": False,
        "progression_length": 0,
        "direction_consistent": False,
        "temporal_consistent": False,
        "bus_speed_plausible": False,
        "bus_evidence_present": False,
    }
    if bus_stop_index is None or bus_stops is None or bus_stops.empty:
        return empty
    radius = settings.radii_m["bus_stop"]
    start = bus_stop_index.query(start_latitude, start_longitude, radius_m=radius)
    end = bus_stop_index.query(end_latitude, end_longitude, radius_m=radius)
    nearby = pd.concat([start, end], ignore_index=True).drop_duplicates("stop_id")
    proximity = _bounded(1.0 - float(min(start["distance_m"].min() if not start.empty else radius, end["distance_m"].min() if not end.empty else radius)) / radius)
    route_score = 0.0
    sequence = 0.0
    route_id = route_no = None
    route_candidates: list[str] = []
    matched_stop_ids = [str(value) for value in nearby.get("stop_id", pd.Series(dtype=str)).tolist()]
    route_consistency_count = 0
    progression_length = 0
    if bus_route_stops is not None and not bus_route_stops.empty and not nearby.empty:
        route_rows = bus_route_stops[bus_route_stops["stop_id"].isin(nearby["stop_id"])]
        counts = route_rows.groupby(["route_id", "route_no"], dropna=False)["stop_id"].nunique().sort_values(ascending=False)
        route_candidates = [f"{key[0]}:{key[1]}" for key in counts.index.tolist()]
        if not counts.empty:
            route_key = counts.index[0]
            route_id, route_no = str(route_key[0]), str(route_key[1])
            matched_count = int(counts.iloc[0])
            route_score = _bounded(matched_count / 3.0)
            # CSV readers may infer numeric route/stop IDs while GPS evidence
            # is normalized to strings. Compare by normalized text so the
            # ordered route is actually selected instead of silently empty.
            selected = bus_route_stops[
                bus_route_stops["route_id"].astype(str).eq(route_id)
                & bus_route_stops["route_no"].astype(str).eq(route_no)
            ]
            sequence = sequence_score(observed_stop_ids, selected)
            selected_stop_ids = set(selected["stop_id"].astype(str))
            route_consistency_count = int(sum(1 for stop_id in observed_stop_ids if str(stop_id) in selected_stop_ids))
            progression_length = route_consistency_count
    nearest = bus_stop_index.nearest(start_latitude, start_longitude) if bus_stop_index is not None else {}
    endpoint_nearest = bus_stop_index.nearest(end_latitude, end_longitude) if bus_stop_index is not None else {}
    nearest_distance = float(min(nearest.get("distance_m", radius), endpoint_nearest.get("distance_m", radius)))
    direction_consistent = bool(sequence >= 0.75 and progression_length >= 2)
    temporal_consistent = bool(len(timestamps) >= 2 and progression_length >= 2)
    bus_speed_plausible = False
    if trajectory and len(trajectory) >= 2 and timestamps and len(timestamps) >= 2:
        try:
            elapsed = (timestamps[-1] - timestamps[0]).total_seconds()
            # Endpoint displacement is only a plausibility guard, not a mode rule.
            lat_delta = float(trajectory[-1][0]) - float(trajectory[0][0])
            lon_delta = float(trajectory[-1][1]) - float(trajectory[0][1])
            displacement_km = math.sqrt(lat_delta * lat_delta + lon_delta * lon_delta) * 111.0
            speed_kmh = displacement_km / (elapsed / 3600.0) if elapsed > 0 else 0.0
            bus_speed_plausible = 0.5 <= speed_kmh <= 100.0
        except (AttributeError, TypeError, ValueError, ZeroDivisionError):
            bus_speed_plausible = False
    context_score = _weighted({"bus_proximity": proximity, "bus_route": route_score, "bus_sequence": sequence, "bus_live": live_match_score}, settings.weights)
    reason = "nearby stops only" if route_id is None else "route and stop evidence"
    return {
        **empty,
        "nearby_bus_stop_count": int(len(nearby)),
        "matched_bus_route_id": route_id,
        "matched_bus_route_no": route_no,
        "matched_bus_stop_count": int(nearby["stop_id"].isin(bus_route_stops["stop_id"]).sum()) if bus_route_stops is not None else 0,
        "bus_stop_proximity_score": proximity,
        "bus_route_match_score": route_score,
        "bus_sequence_score": sequence,
        "bus_context_score": context_score,
        "bus_evidence_reason": reason,
        "nearest_bus_stop_id": str(nearest.get("stop_id")) if nearest.get("stop_id") is not None else None,
        "nearest_bus_stop_distance_m": nearest_distance,
        "matched_stop_ids": matched_stop_ids,
        "route_candidate_ids": route_candidates,
        "route_candidate_count": len(route_candidates),
        "route_consistent": bool(route_consistency_count >= 2),
        "route_consistency_count": route_consistency_count,
        "ordered_stop_progression": bool(sequence >= 0.75 and progression_length >= 2),
        "progression_length": progression_length,
        "direction_consistent": direction_consistent,
        "temporal_consistent": temporal_consistent,
        "bus_speed_plausible": bus_speed_plausible,
        "bus_evidence_present": bool(context_score >= settings.resolver.get("minimum_context_score", 0.35)),
    }


def _station_candidates(index: GeoPointIndex | None, latitude: float, longitude: float, radius_m: float) -> pd.DataFrame:
    return index.query(latitude, longitude, radius_m=radius_m) if index is not None else pd.DataFrame()


def subway_context(
    *,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    station_index: GeoPointIndex | None,
    stations: pd.DataFrame | None,
    ml_rail_probability: float = 0.0,
    timetable_compatible: bool | None = None,
    trajectory: Sequence[tuple[float, float]] = (),
    station_history: Sequence[tuple[str, str]] = (),
    settings: TransitSettings | None = None,
) -> dict[str, object]:
    settings = settings or load_settings()
    empty = {
        "subway_context_score": 0.0,
        "subway_proximity_score": 0.0,
        "subway_line_score": 0.0,
        "subway_sequence_score": None,
        "subway_timetable_score": 0.0,
        "subway_corridor_proximity_score": 0.0,
        "subway_observed_station_count": 0,
        "subway_current_observed_station_count": 0,
        "subway_observed_station_ids": [],
        "subway_current_observed_station_ids": [],
        "subway_current_observed_lines": [],
        "matched_subway_line": None,
        "subway_start_station_id": None,
        "subway_end_station_id": None,
        "subway_evidence_reason": "subway reference unavailable",
    }
    if station_index is None or stations is None or stations.empty:
        return empty
    radius = settings.radii_m["subway_station"]
    start = _station_candidates(station_index, start_latitude, start_longitude, radius)
    end = _station_candidates(station_index, end_latitude, end_longitude, radius)
    start_row = start.iloc[0] if not start.empty else None
    end_row = end.iloc[0] if not end.empty else None
    start_lines = set(stations[stations["station_id"] == start_row["station_id"]]["line"].astype(str)) if start_row is not None else set()
    end_lines = set(stations[stations["station_id"] == end_row["station_id"]]["line"].astype(str)) if end_row is not None else set()
    common = sorted(start_lines & end_lines)
    corridor_radius = radius * 2.0
    observed: list[tuple[str, str, float]] = []
    for latitude, longitude in trajectory:
        nearest = station_index.nearest(latitude, longitude)
        distance = float(nearest["distance_m"])
        if distance <= corridor_radius:
            observed.append((str(nearest["station_id"]), str(nearest["line"]), distance))
    observed_ids: list[str] = []
    observed_lines: dict[str, list[str]] = {}
    for station_id, line, _distance in observed:
        if not observed_ids or observed_ids[-1] != station_id:
            observed_ids.append(station_id)
        observed_lines.setdefault(line, [])
        if station_id not in observed_lines[line]:
            observed_lines[line].append(station_id)
    line_from_trajectory = max(observed_lines, key=lambda line: len(observed_lines[line]), default=None)
    current_ids = list(observed_ids)
    current_lines = sorted(observed_lines)
    combined_lines: dict[str, list[str]] = {}
    for station_id, line in station_history:
        combined_lines.setdefault(str(line), [])
        if str(station_id) not in combined_lines[str(line)]:
            combined_lines[str(line)].append(str(station_id))
    for line, station_ids in observed_lines.items():
        combined_lines.setdefault(line, [])
        for station_id in station_ids:
            if station_id not in combined_lines[line]:
                combined_lines[line].append(station_id)
    history_line = max(combined_lines, key=lambda line: len(combined_lines[line]), default=None)
    matched_line = common[0] if common else history_line or line_from_trajectory
    line_score = 1.0 if matched_line is not None else 0.0
    endpoint_proximity = _bounded(1 - (float(start_row["distance_m"]) + float(end_row["distance_m"])) / (2 * radius)) if start_row is not None and end_row is not None else 0.0
    corridor_proximity = _bounded(1 - min((distance for _, _, distance in observed), default=corridor_radius) / corridor_radius)
    proximity = max(endpoint_proximity, corridor_proximity)
    line_station_ids = combined_lines.get(str(matched_line), []) if matched_line is not None else []
    sequence = _bounded((len(line_station_ids) - 1) / 2.0) if len(line_station_ids) >= 2 else 0.0
    timetable_score = 1.0 if timetable_compatible is True else 0.0
    score = _weighted({"subway_proximity": proximity, "subway_line": line_score, "subway_timetable": timetable_score, "subway_sequence": sequence}, settings.weights)
    return {
        **empty,
        "subway_context_score": score,
        "subway_proximity_score": proximity,
        "subway_line_score": line_score,
        "subway_corridor_proximity_score": corridor_proximity,
        "subway_observed_station_count": len(line_station_ids),
        "subway_current_observed_station_count": len(observed_lines.get(str(matched_line), [])) if matched_line is not None else len(current_ids),
        "subway_observed_station_ids": line_station_ids,
        "subway_current_observed_station_ids": observed_lines.get(str(matched_line), current_ids) if matched_line is not None else current_ids,
        "subway_current_observed_lines": current_lines,
        "subway_sequence_score": sequence,
        "subway_timetable_score": timetable_score,
        "matched_subway_line": matched_line,
        "subway_start_station_id": str(start_row["station_id"]) if start_row is not None else (line_station_ids[0] if line_station_ids else None),
        "subway_end_station_id": str(end_row["station_id"]) if end_row is not None else (line_station_ids[-1] if line_station_ids else None),
        "subway_evidence_reason": "same line, station sequence and trajectory proximity" if len(line_station_ids) >= 2 else "trajectory station proximity" if line_station_ids else "endpoint proximity only",
    }


def korail_context(
    *,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    station_index: GeoPointIndex | None,
    ml_rail_probability: float,
    movement_score: float = 0.0,
    settings: TransitSettings | None = None,
) -> dict[str, object]:
    settings = settings or load_settings()
    if station_index is None:
        return {"train_context_score": 0.0, "matched_train_start_station": None, "matched_train_end_station": None, "train_evidence_reason": "korail reference unavailable"}
    radius = settings.radii_m["korail_station"]
    start, end = station_index.query(start_latitude, start_longitude, radius_m=radius), station_index.query(end_latitude, end_longitude, radius_m=radius)
    proximity = _bounded(1 - ((float(start.iloc[0]["distance_m"]) if not start.empty else radius) + (float(end.iloc[0]["distance_m"]) if not end.empty else radius)) / (2 * radius))
    score = _weighted({"korail_proximity": proximity, "korail_ml_probability": ml_rail_probability, "korail_movement": movement_score}, settings.weights)
    return {"train_context_score": score, "matched_train_start_station": str(start.iloc[0]["station_id"]) if not start.empty else None, "matched_train_end_station": str(end.iloc[0]["station_id"]) if not end.empty else None, "train_evidence_reason": "station proximity with rail probability" if score else "no strong train evidence"}
