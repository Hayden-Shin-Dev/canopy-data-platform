from datetime import timezone

from src.integration.gps_contract import validate_gps_event


def _payload(**overrides):
    event = {
        "schema_version": "1.0",
        "trip_id": "trip-1",
        "device_id": "device-1",
        "sequence": 0,
        "timestamp": "2026-08-29T12:00:00Z",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "horizontal_accuracy_m": 8.0,
        "altitude_m": 35.0,
        "vertical_accuracy_m": 3.0,
        "speed_mps": 4.2,
        "course_deg": 90.0,
    }
    event.update(overrides)
    return event


def test_valid_event_is_normalized_to_utc():
    result = validate_gps_event(_payload(timestamp="2026-08-29T21:00:00+09:00"))

    assert result.accepted is True
    assert result.errors == ()
    assert result.event is not None
    assert result.event.timestamp.tzinfo == timezone.utc
    assert result.event.timestamp.hour == 12


def test_missing_required_field_is_rejected():
    payload = _payload()
    del payload["latitude"]

    result = validate_gps_event(payload)

    assert result.accepted is False
    assert "missing:latitude" in result.errors
    assert result.event is None


def test_coordinate_and_course_ranges_are_rejected():
    result = validate_gps_event(_payload(latitude=91, course_deg=360))

    assert result.accepted is False
    assert "out_of_range:latitude" in result.errors
    assert "out_of_range:course_deg" in result.errors


def test_ios_invalid_sentinels_are_warning_and_normalized_to_none():
    result = validate_gps_event(
        _payload(
            horizontal_accuracy_m=-1,
            altitude_m=-9999,
            vertical_accuracy_m=-1,
            speed_mps=-1,
            course_deg=-1,
        )
    )

    assert result.accepted is True
    assert result.event is not None
    assert result.event.horizontal_accuracy_m is None
    assert result.event.altitude_m is None
    assert result.event.vertical_accuracy_m is None
    assert result.event.speed_mps is None
    assert result.event.course_deg is None
    assert len(result.warnings) == 5


def test_non_sentinel_negative_accuracy_is_rejected():
    result = validate_gps_event(_payload(horizontal_accuracy_m=-2))

    assert result.accepted is False
    assert "negative:horizontal_accuracy_m" in result.errors
