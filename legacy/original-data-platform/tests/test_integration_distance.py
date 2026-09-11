from src.integration.distance import haversine_distance_km, trajectory_distance_km
from src.integration.gps_contract import validate_gps_event


def _event(sequence, longitude):
    payload = {
        "schema_version": "1.0",
        "trip_id": "trip-1",
        "device_id": "device-1",
        "sequence": sequence,
        "timestamp": f"2026-08-29T12:00:{sequence:02d}Z",
        "latitude": 37.5665,
        "longitude": longitude,
        "horizontal_accuracy_m": 5,
        "altitude_m": 30,
        "vertical_accuracy_m": 5,
        "speed_mps": 2,
        "course_deg": 90,
    }
    result = validate_gps_event(payload)
    assert result.event is not None
    return result.event


def test_haversine_zero_distance_is_zero():
    assert haversine_distance_km(37.5, 127.0, 37.5, 127.0) == 0


def test_trajectory_distance_sums_consecutive_segments():
    events = [_event(0, 126.9780), _event(1, 126.9790), _event(2, 126.9800)]

    distance = trajectory_distance_km(events)

    assert 0.17 < distance < 0.19
