"""Trip lifecycle and quality-aware ingestion for canonical GPS events."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from .distance import haversine_distance_km
from .gps_contract import GpsEvent, ValidationResult, validate_gps_event


class TripStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class IngestionDecision:
    accepted: bool
    event: GpsEvent | None
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass
class TripSession:
    trip_id: str
    device_id: str
    status: TripStatus = TripStatus.CREATED
    events: list[GpsEvent] = field(default_factory=list)
    rejected_count: int = 0
    warning_counts: Counter[str] = field(default_factory=Counter)
    rejection_counts: Counter[str] = field(default_factory=Counter)
    result: dict[str, Any] | None = None
    failure_reason: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "trip_id": self.trip_id,
            "device_id": self.device_id,
            "status": self.status.value,
            "accepted_event_count": len(self.events),
            "rejected_event_count": self.rejected_count,
            "warning_counts": dict(sorted(self.warning_counts.items())),
            "rejection_counts": dict(sorted(self.rejection_counts.items())),
            "first_timestamp": self.events[0].timestamp.isoformat().replace("+00:00", "Z") if self.events else None,
            "last_timestamp": self.events[-1].timestamp.isoformat().replace("+00:00", "Z") if self.events else None,
            "result": self.result,
            "failure_reason": self.failure_reason,
        }


class TripIngestor:
    """Receive one canonical event at a time and retain an auditable decision log."""

    def __init__(self, *, gap_warning_seconds: float = 120.0, max_jump_speed_mps: float = 80.0, accuracy_warning_m: float = 100.0):
        self.gap_warning_seconds = gap_warning_seconds
        self.max_jump_speed_mps = max_jump_speed_mps
        self.accuracy_warning_m = accuracy_warning_m
        self.sessions: dict[str, TripSession] = {}

    def start_trip(self, trip_id: str, device_id: str) -> TripSession:
        if not trip_id.strip() or not device_id.strip():
            raise ValueError("trip_id and device_id are required")
        if trip_id in self.sessions:
            raise ValueError(f"trip already exists: {trip_id}")
        session = TripSession(trip_id=trip_id, device_id=device_id)
        self.sessions[trip_id] = session
        return session

    def _reject(self, session: TripSession, reasons: list[str], warnings: list[str] | None = None) -> IngestionDecision:
        session.rejected_count += 1
        session.rejection_counts.update(reasons)
        if warnings:
            session.warning_counts.update(warnings)
        return IngestionDecision(False, None, tuple(reasons), tuple(warnings or ()))

    def ingest(self, payload: Mapping[str, Any]) -> IngestionDecision:
        trip_id = str(payload.get("trip_id", ""))
        if trip_id not in self.sessions:
            raise KeyError(f"trip has not been started: {trip_id}")
        session = self.sessions[trip_id]
        if session.status not in {TripStatus.CREATED, TripStatus.ACTIVE}:
            return self._reject(session, [f"trip_not_accepting:{session.status.value}"])
        validation: ValidationResult = validate_gps_event(payload)
        if not validation.accepted or validation.event is None:
            return self._reject(session, list(validation.errors), list(validation.warnings))
        event = validation.event
        reasons: list[str] = []
        warnings = list(validation.warnings)
        if event.trip_id != session.trip_id:
            reasons.append("trip_id_mismatch")
        if event.device_id != session.device_id:
            reasons.append("device_id_mismatch")
        if session.events:
            previous = session.events[-1]
            if event.sequence == previous.sequence:
                reasons.append("duplicate_sequence")
            elif event.sequence < previous.sequence:
                reasons.append("out_of_order_sequence")
            if event.timestamp <= previous.timestamp:
                reasons.append("out_of_order_timestamp")
            else:
                gap = (event.timestamp - previous.timestamp).total_seconds()
                if gap > self.gap_warning_seconds:
                    warnings.append("large_timestamp_gap")
                jump_speed = haversine_distance_km(previous.latitude, previous.longitude, event.latitude, event.longitude) * 1000 / gap
                if jump_speed > self.max_jump_speed_mps:
                    reasons.append("gps_jump_outlier")
        if event.horizontal_accuracy_m is None:
            warnings.append("horizontal_accuracy_unavailable")
        elif event.horizontal_accuracy_m > self.accuracy_warning_m:
            warnings.append("low_horizontal_accuracy")
        if reasons:
            return self._reject(session, reasons, warnings)
        session.events.append(event)
        session.status = TripStatus.ACTIVE
        session.warning_counts.update(warnings)
        return IngestionDecision(True, event, (), tuple(warnings))

    def stop_trip(self, trip_id: str) -> TripSession:
        session = self._get_session(trip_id)
        if session.status not in {TripStatus.CREATED, TripStatus.ACTIVE}:
            raise ValueError(f"trip cannot stop from status {session.status.value}")
        session.status = TripStatus.PROCESSING
        return session

    def complete_trip(self, trip_id: str, result: Mapping[str, Any]) -> TripSession:
        session = self._get_session(trip_id)
        if session.status != TripStatus.PROCESSING:
            raise ValueError(f"trip cannot complete from status {session.status.value}")
        session.result = dict(result)
        session.status = TripStatus.COMPLETED
        return session

    def fail_trip(self, trip_id: str, reason: str) -> TripSession:
        session = self._get_session(trip_id)
        session.failure_reason = reason
        session.status = TripStatus.FAILED
        return session

    def _get_session(self, trip_id: str) -> TripSession:
        try:
            return self.sessions[trip_id]
        except KeyError as exc:
            raise KeyError(f"unknown trip: {trip_id}") from exc
