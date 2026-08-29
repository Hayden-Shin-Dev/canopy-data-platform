from src.integration.ingestion import TripIngestor, TripStatus


def _payload(sequence=0, *, timestamp=None, latitude=37.5665, longitude=126.9780, **overrides):
    event = {
        "schema_version": "1.0",
        "trip_id": "trip-1",
        "device_id": "device-1",
        "sequence": sequence,
        "timestamp": timestamp or f"2026-08-29T12:00:{sequence:02d}Z",
        "latitude": latitude,
        "longitude": longitude,
        "horizontal_accuracy_m": 5,
        "altitude_m": 30,
        "vertical_accuracy_m": 5,
        "speed_mps": 2,
        "course_deg": 90,
    }
    event.update(overrides)
    return event


def test_trip_lifecycle_reaches_completed():
    ingestor = TripIngestor()
    ingestor.start_trip("trip-1", "device-1")
    assert ingestor.ingest(_payload()).accepted
    session = ingestor.stop_trip("trip-1")
    assert session.status is TripStatus.PROCESSING
    ingestor.complete_trip("trip-1", {"final_mode": "walk"})
    assert ingestor.sessions["trip-1"].status is TripStatus.COMPLETED


def test_duplicate_and_out_of_order_events_are_rejected():
    ingestor = TripIngestor()
    ingestor.start_trip("trip-1", "device-1")
    assert ingestor.ingest(_payload(0)).accepted
    duplicate = ingestor.ingest(_payload(0))
    assert ingestor.ingest(_payload(1)).accepted
    reverse = ingestor.ingest(_payload(0, timestamp="2026-08-29T11:59:59Z"))

    assert duplicate.accepted is False
    assert "duplicate_sequence" in duplicate.reasons
    assert reverse.accepted is False
    assert "out_of_order_sequence" in reverse.reasons


def test_large_gap_is_accepted_with_warning():
    ingestor = TripIngestor()
    ingestor.start_trip("trip-1", "device-1")
    ingestor.ingest(_payload(0))
    result = ingestor.ingest(_payload(1, timestamp="2026-08-29T12:03:00Z"))

    assert result.accepted is True
    assert "large_timestamp_gap" in result.warnings


def test_gps_jump_is_rejected_without_dropping_previous_event():
    ingestor = TripIngestor()
    ingestor.start_trip("trip-1", "device-1")
    ingestor.ingest(_payload(0))
    result = ingestor.ingest(_payload(1, latitude=35.0, longitude=129.0))

    assert result.accepted is False
    assert "gps_jump_outlier" in result.reasons
    assert len(ingestor.sessions["trip-1"].events) == 1


def test_quality_warning_is_recorded_for_missing_accuracy():
    ingestor = TripIngestor()
    ingestor.start_trip("trip-1", "device-1")
    result = ingestor.ingest(_payload(horizontal_accuracy_m=-1))

    assert result.accepted is True
    assert "horizontal_accuracy_unavailable" in result.warnings
    assert ingestor.sessions["trip-1"].summary()["warning_counts"]["horizontal_accuracy_unavailable"] == 1
