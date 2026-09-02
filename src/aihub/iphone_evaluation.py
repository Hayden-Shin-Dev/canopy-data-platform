"""Local-only iPhone prediction logging and manually labelled route evaluation."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from sklearn.metrics import accuracy_score, classification_report, f1_score

from .config import CANOPY_MODES


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def append_prediction(path: str | Path, record: dict[str, object]) -> None:
    required = {
        "schema_version", "journey_id", "model_version", "git_sha", "timestamp",
        "latitude", "longitude", "horizontal_accuracy_m", "altitude_m",
        "movement_probabilities", "movement_prediction", "temporal_prediction",
        "transit_applicability", "transit_evidence", "final_prediction",
    }
    missing = sorted(required - set(record))
    if missing:
        raise ValueError(f"iPhone prediction log is missing fields: {missing}")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def _sequence(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if not output or output[-1] != value:
            output.append(value)
    return output


def evaluate_iphone_journey(
    predictions_jsonl: str | Path,
    manual_segments_csv: str | Path,
    output_json: str | Path,
) -> dict[str, object]:
    with Path(predictions_jsonl).open("r", encoding="utf-8") as stream:
        predictions = [json.loads(line) for line in stream if line.strip()]
    with Path(manual_segments_csv).open("r", encoding="utf-8-sig", newline="") as stream:
        segments = list(csv.DictReader(stream))
    if not predictions or not segments:
        raise ValueError("prediction logs and manual segments must not be empty")
    versions = {(row["journey_id"], row["model_version"], row["git_sha"]) for row in predictions}
    if len(versions) != 1:
        raise ValueError("one journey must use one model version and git SHA")
    parsed_segments = [
        (_timestamp(row["segment_start"]), _timestamp(row["segment_end"]), row["true_mode"])
        for row in segments
    ]
    expected: list[str] = []
    predicted: list[str] = []
    collecting = 0
    for row in predictions:
        final_mode = row.get("final_prediction")
        if final_mode is None:
            collecting += 1
            continue
        observed_at = _timestamp(str(row["timestamp"]))
        true_mode = next(
            (mode for start, end, mode in parsed_segments if start <= observed_at < end),
            None,
        )
        if true_mode is not None:
            expected.append(str(true_mode))
            predicted.append(str(final_mode))
    if not expected:
        raise ValueError("no prediction timestamp overlaps manual Ground Truth")
    transition_latency = []
    for start, _end, mode in parsed_segments[1:]:
        matched = next(
            (
                _timestamp(str(row["timestamp"]))
                for row in predictions
                if _timestamp(str(row["timestamp"])) >= start and row.get("final_prediction") == mode
            ),
            None,
        )
        transition_latency.append(
            {"transition_time": start.isoformat(), "true_mode": mode, "latency_seconds": (matched - start).total_seconds() if matched else None}
        )
    true_sequence = _sequence([mode for _start, _end, mode in parsed_segments])
    predicted_sequence = _sequence(predicted)
    result = {
        "status": "PASS",
        "journey_id": predictions[0]["journey_id"],
        "model_version": predictions[0]["model_version"],
        "git_sha": predictions[0]["git_sha"],
        "matched_prediction_count": len(expected),
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_f1": float(f1_score(expected, predicted, labels=list(CANOPY_MODES), average="macro", zero_division=0)),
        "classification_report": classification_report(expected, predicted, labels=list(CANOPY_MODES), output_dict=True, zero_division=0),
        "true_sequence": true_sequence,
        "predicted_sequence": predicted_sequence,
        "sequence_exact_match": predicted_sequence == true_sequence,
        "transition_latency": transition_latency,
        "collecting_count": collecting,
        "prediction_coverage": (len(predictions) - collecting) / len(predictions),
    }
    destination = Path(output_json)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
