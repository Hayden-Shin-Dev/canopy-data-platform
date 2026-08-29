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
    sequence = route_stops.drop_duplicates("stop_id").set_index("stop_id")["stop_sequence"].to_dict()
    values = [float(sequence[stop]) for stop in observed_stop_ids if stop in sequence]
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
    if bus_route_stops is not None and not bus_route_stops.empty and not nearby.empty:
        route_rows = bus_route_stops[bus_route_stops["stop_id"].isin(nearby["stop_id"])]
        counts = route_rows.groupby(["route_id", "route_no"], dropna=False)["stop_id"].nunique().sort_values(ascending=False)
        if not counts.empty:
            route_key = counts.index[0]
            route_id, route_no = str(route_key[0]), str(route_key[1])
            matched_count = int(counts.iloc[0])
            route_score = _bounded(matched_count / 3.0)
            selected = bus_route_stops[(bus_route_stops["route_id"] == route_id) & (bus_route_stops["route_no"] == route_no)]
            sequence = sequence_score(observed_stop_ids, selected)
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
    settings: TransitSettings | None = None,
) -> dict[str, object]:
    settings = settings or load_settings()
    empty = {
        "subway_context_score": 0.0,
        "subway_proximity_score": 0.0,
        "subway_line_score": 0.0,
        "subway_sequence_score": None,
        "subway_timetable_score": 0.0,
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
    if start.empty or end.empty:
        return empty
    start_row, end_row = start.iloc[0], end.iloc[0]
    start_lines = set(stations[stations["station_id"] == start_row["station_id"]]["line"].astype(str))
    end_lines = set(stations[stations["station_id"] == end_row["station_id"]]["line"].astype(str))
    common = sorted(start_lines & end_lines)
    line_score = 1.0 if common else 0.0
    proximity = _bounded(1 - (float(start_row["distance_m"]) + float(end_row["distance_m"])) / (2 * radius))
    timetable_score = 1.0 if timetable_compatible is True else 0.0
    score = _weighted({"subway_proximity": proximity, "subway_line": line_score, "subway_timetable": timetable_score, "subway_sequence": 0.0}, settings.weights)
    return {
        **empty,
        "subway_context_score": score,
        "subway_proximity_score": proximity,
        "subway_line_score": line_score,
        "subway_timetable_score": timetable_score,
        "matched_subway_line": common[0] if common else None,
        "subway_start_station_id": str(start_row["station_id"]),
        "subway_end_station_id": str(end_row["station_id"]),
        "subway_evidence_reason": "same line and endpoint proximity" if common else "endpoint proximity only",
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
