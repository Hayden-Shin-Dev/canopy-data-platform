from pathlib import Path

import pytest

from src.integration.replay import ReplayEngine, read_replay_csv


def _payload(sequence):
    return {
        "schema_version": "1.0", "trip_id": "trip-replay", "device_id": "device-1", "sequence": sequence,
        "timestamp": f"2026-08-29T12:00:{sequence:02d}Z", "latitude": 37.5665, "longitude": 126.978 + sequence * 0.0001,
        "horizontal_accuracy_m": 5, "altitude_m": 30, "vertical_accuracy_m": 5, "speed_mps": 2, "course_deg": 90,
    }


def test_replay_calls_ingestion_for_each_event_in_order():
    seen = []
    result = ReplayEngine(speed="instant").stream([_payload(0), _payload(1), _payload(2)], on_update=lambda update: seen.append(update.index))

    assert result.status == "STREAMED"
    assert seen == [0, 1, 2]
    assert [update.decision.accepted for update in result.updates] == [True, True, True]
    assert result.session.summary()["accepted_event_count"] == 3


def test_replay_preserves_rejected_event_decision():
    rows = [_payload(0), _payload(0)]

    result = ReplayEngine(speed="instant").stream(rows)

    assert result.updates[1].decision.accepted is False
    assert "duplicate_sequence" in result.updates[1].decision.reasons
    assert result.session.summary()["rejected_event_count"] == 1


def test_replay_reads_utf8_csv(tmp_path: Path):
    csv_path = tmp_path / "events.csv"
    csv_path.write_text("schema_version,trip_id,device_id,sequence,timestamp,latitude,longitude,horizontal_accuracy_m,altitude_m,vertical_accuracy_m,speed_mps,course_deg\n1.0,t,d,0,2026-08-29T12:00:00Z,1,2,3,4,5,6,7\n", encoding="utf-8")

    rows = read_replay_csv(csv_path)

    assert rows[0]["trip_id"] == "t"


def test_replay_rejects_unknown_speed():
    with pytest.raises(ValueError):
        ReplayEngine(speed=2)


def test_replay_rejects_ground_truth_columns(tmp_path: Path):
    csv_path = tmp_path / "labelled.csv"
    csv_path.write_text(
        "schema_version,trip_id,device_id,sequence,timestamp,latitude,longitude,"
        "horizontal_accuracy_m,altitude_m,vertical_accuracy_m,speed_mps,course_deg,ground_truth_mode\n"
        "1.0,t,d,0,2026-08-29T12:00:00Z,1,2,3,4,5,6,7,walk\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="evaluation fields"):
        read_replay_csv(csv_path)
