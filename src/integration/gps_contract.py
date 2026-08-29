"""Canonical GPS event contract shared by replay and a future iPhone client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Mapping


REQUIRED_FIELDS = (
    "schema_version",
    "trip_id",
    "device_id",
    "sequence",
    "timestamp",
    "latitude",
    "longitude",
    "horizontal_accuracy_m",
    "altitude_m",
    "vertical_accuracy_m",
    "speed_mps",
    "course_deg",
)
INVALID_ACCURACY_SENTINEL = -1.0
INVALID_ALTITUDE_SENTINEL = -9999.0
INVALID_SPEED_SENTINEL = -1.0
INVALID_COURSE_SENTINEL = -1.0


@dataclass(frozen=True)
class GpsEvent:
    """Normalized event values used by every ingestion path."""

    schema_version: str
    trip_id: str
    device_id: str
    sequence: int
    timestamp: datetime
    latitude: float
    longitude: float
    horizontal_accuracy_m: float | None
    altitude_m: float | None
    vertical_accuracy_m: float | None
    speed_mps: float | None
    course_deg: float | None
    source: str | None = None
    is_simulated: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-compatible values while retaining UTC explicitly."""

        result = {
            "schema_version": self.schema_version,
            "trip_id": self.trip_id,
            "device_id": self.device_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "horizontal_accuracy_m": self.horizontal_accuracy_m,
            "altitude_m": self.altitude_m,
            "vertical_accuracy_m": self.vertical_accuracy_m,
            "speed_mps": self.speed_mps,
            "course_deg": self.course_deg,
        }
        if self.source is not None:
            result["source"] = self.source
        result["is_simulated"] = self.is_simulated
        return result


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    event: GpsEvent | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _finite_number(payload: Mapping[str, Any], name: str, errors: list[str]) -> float | None:
    value = payload.get(name)
    if value is None:
        errors.append(f"missing:{name}")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"invalid_number:{name}")
        return None
    if not math.isfinite(number):
        errors.append(f"non_finite:{name}")
        return None
    return number


def _sentinel_or_nonnegative(value: float | None, name: str, sentinel: float, errors: list[str], warnings: list[str]) -> float | None:
    if value is None:
        return None
    if value == sentinel:
        warnings.append(f"invalid_sentinel:{name}")
        return None
    if value < 0:
        errors.append(f"negative:{name}")
        return None
    return value


def _parse_timestamp(value: Any, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append("invalid_timestamp")
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        errors.append("invalid_timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append("timestamp_must_include_timezone")
        return None
    return parsed.astimezone(timezone.utc)


def validate_gps_event(payload: Mapping[str, Any]) -> ValidationResult:
    """Validate and normalize one event without mutating the input mapping."""

    errors: list[str] = [f"missing:{name}" for name in REQUIRED_FIELDS if name not in payload]
    warnings: list[str] = []
    if errors:
        return ValidationResult(False, None, tuple(errors), ())

    schema_version = str(payload["schema_version"]).strip()
    trip_id = str(payload["trip_id"]).strip()
    device_id = str(payload["device_id"]).strip()
    if not schema_version:
        errors.append("empty:schema_version")
    if not trip_id:
        errors.append("empty:trip_id")
    if not device_id:
        errors.append("empty:device_id")

    try:
        sequence = int(payload["sequence"])
    except (TypeError, ValueError):
        errors.append("invalid_number:sequence")
        sequence = -1
    if sequence < 0:
        errors.append("negative:sequence")

    timestamp = _parse_timestamp(payload["timestamp"], errors)
    latitude = _finite_number(payload, "latitude", errors)
    longitude = _finite_number(payload, "longitude", errors)
    if latitude is not None and not -90 <= latitude <= 90:
        errors.append("out_of_range:latitude")
    if longitude is not None and not -180 <= longitude <= 180:
        errors.append("out_of_range:longitude")

    horizontal = _sentinel_or_nonnegative(_finite_number(payload, "horizontal_accuracy_m", errors), "horizontal_accuracy_m", INVALID_ACCURACY_SENTINEL, errors, warnings)
    altitude = _finite_number(payload, "altitude_m", errors)
    if altitude == INVALID_ALTITUDE_SENTINEL:
        warnings.append("invalid_sentinel:altitude_m")
        altitude = None
    vertical = _sentinel_or_nonnegative(_finite_number(payload, "vertical_accuracy_m", errors), "vertical_accuracy_m", INVALID_ACCURACY_SENTINEL, errors, warnings)
    speed = _sentinel_or_nonnegative(_finite_number(payload, "speed_mps", errors), "speed_mps", INVALID_SPEED_SENTINEL, errors, warnings)
    course = _finite_number(payload, "course_deg", errors)
    if course == INVALID_COURSE_SENTINEL:
        warnings.append("invalid_sentinel:course_deg")
        course = None
    elif course is not None and not 0 <= course < 360:
        errors.append("out_of_range:course_deg")

    if errors or timestamp is None or latitude is None or longitude is None:
        return ValidationResult(False, None, tuple(errors), tuple(warnings))
    event = GpsEvent(
        schema_version=schema_version,
        trip_id=trip_id,
        device_id=device_id,
        sequence=sequence,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        horizontal_accuracy_m=horizontal,
        altitude_m=altitude,
        vertical_accuracy_m=vertical,
        speed_mps=speed,
        course_deg=course,
        source=str(payload["source"]).strip() if payload.get("source") is not None else None,
        is_simulated=bool(payload.get("is_simulated", False)),
    )
    return ValidationResult(True, event, (), tuple(warnings))
