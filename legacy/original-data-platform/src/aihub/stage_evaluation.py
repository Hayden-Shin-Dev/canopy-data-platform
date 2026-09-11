"""Labelled AI-Hub Movement, Temporal, Transit and Final stage evaluation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from scripts.build_aihub_duration_windows import _join, _normalized_uid, joined_window_points
from src.integration.gps_contract import GpsEvent
from src.integration.pipeline import TransitRuntimeReferences, build_transit_context
from src.integration.segments import smooth_window_modes
from src.transit_context.resolver import resolve_mode
from src.transit_context.settings import load_settings

from .config import CANOPY_MODES
from .ingest import AiHubTrajectory, iter_gps_files, read_trajectory
from .filenames import parse_tmc_filename
from .runtime import predict_event_window


def _metrics(expected: list[str], predicted: list[str]) -> dict[str, object]:
    report = classification_report(
        expected,
        predicted,
        labels=list(CANOPY_MODES),
        output_dict=True,
        zero_division=0,
    )
    return {
        "row_count": len(expected),
        "accuracy": float(accuracy_score(expected, predicted)),
        "macro_f1": float(f1_score(expected, predicted, labels=list(CANOPY_MODES), average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(expected, predicted, labels=list(CANOPY_MODES), average="weighted", zero_division=0)),
        "classification_report": report,
        "confusion_matrix_labels": list(CANOPY_MODES),
        "confusion_matrix": confusion_matrix(expected, predicted, labels=list(CANOPY_MODES)).tolist(),
    }


def _read_without_labels(item: tuple[str, Path, Path]) -> AiHubTrajectory:
    return read_trajectory(*item, strict_label_timestamps=False, read_label_content=False)


def _events(points: tuple, *, user_id: str, trip_id: str) -> list[GpsEvent]:
    return [
        GpsEvent(
            schema_version="1.0",
            trip_id=trip_id,
            device_id=user_id,
            sequence=index,
            timestamp=point.timestamp,
            latitude=point.latitude,
            longitude=point.longitude,
            horizontal_accuracy_m=point.accuracy_m,
            altitude_m=point.altitude_m,
            vertical_accuracy_m=None,
            speed_mps=None,
            course_deg=None,
        )
        for index, point in enumerate(points)
    ]


def evaluate_stages(
    source_root: str | Path,
    split_manifest: str | Path,
    model_path: str | Path,
    output_json: str | Path,
    *,
    split: str = "test",
    workers: int = 16,
    reference_dir: str | Path | None = None,
) -> dict[str, object]:
    manifest = json.loads(Path(split_manifest).read_text(encoding="utf-8"))
    selected_users = {
        _normalized_uid(item["user_id"])
        for item in manifest["groups"]
        if item["split"] == split
    }
    references = TransitRuntimeReferences.from_directory(reference_dir)
    records_by_sequence: dict[str, list[dict[str, object]]] = defaultdict(list)
    previous: dict[str, AiHubTrajectory] = {}
    applicability = Counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for source_split in ("Training", "Validation"):
            selected_files = (
                item
                for item in iter_gps_files(source_root, source_split)
                if _normalized_uid(parse_tmc_filename(item[1]).uid) in selected_users
            )
            for trajectory in executor.map(_read_without_labels, selected_files, buffersize=max(2, workers * 2)):
                prior = previous.get(trajectory.user_id)
                previous[trajectory.user_id] = trajectory
                if prior is None:
                    continue
                feature_row = _join(prior, trajectory)
                if feature_row is None:
                    continue
                points = joined_window_points(prior, trajectory)
                events = _events(points, user_id=trajectory.user_id, trip_id=str(feature_row["trajectory_id"]))
                movement = predict_event_window(model_path, events)
                if movement["status"] != "READY":
                    continue
                probabilities = dict(movement["probabilities"])
                raw_mode = str(movement["predicted_mode"])
                neutral_context = {
                    "transit_applicability": "NOT_APPLICABLE",
                    "bus_applicability": "NOT_APPLICABLE",
                    "rail_applicability": "NOT_APPLICABLE",
                }
                temporal_decision = resolve_mode(probabilities, context=neutral_context)
                transit_context = build_transit_context(events, probabilities, references)
                transit_decision = resolve_mode(probabilities, context=transit_context)
                applicability[str(transit_context["transit_applicability"])] += 1
                sequence_key = f"{trajectory.user_id}:{trajectory.canonical_mode}"
                records_by_sequence[sequence_key].append(
                    {
                        "ground_truth": trajectory.canonical_mode,
                        "movement": raw_mode,
                        "window": SimpleNamespace(predicted_mode=raw_mode, confidence=movement["confidence"]),
                        "temporal_decision": temporal_decision,
                        "transit_decision": transit_decision,
                        "transit_context": transit_context,
                    }
                )

    settings = load_settings()
    expected: list[str] = []
    movement_predictions: list[str] = []
    temporal_predictions: list[str] = []
    transit_predictions: list[str] = []
    final_predictions: list[str] = []
    for user_records in records_by_sequence.values():
        temporal_records = [
            {"window": row["window"], "decision": row["temporal_decision"], "transit_context": {}}
            for row in user_records
        ]
        final_records = [
            {"window": row["window"], "decision": row["transit_decision"], "transit_context": row["transit_context"]}
            for row in user_records
        ]
        temporal_modes = smooth_window_modes(
            temporal_records,
            minimum_context_score=settings.resolver["minimum_context_score"],
            minimum_ml_confidence=settings.resolver["minimum_ml_confidence"],
            pre_transit_bike_max_windows=int(settings.resolver.get("pre_transit_bike_max_windows", 2)),
            pre_transit_bike_max_confidence=settings.resolver.get("pre_transit_bike_max_confidence", 0.75),
        )
        final_modes = smooth_window_modes(
            final_records,
            minimum_context_score=settings.resolver["minimum_context_score"],
            minimum_ml_confidence=settings.resolver["minimum_ml_confidence"],
            pre_transit_bike_max_windows=int(settings.resolver.get("pre_transit_bike_max_windows", 2)),
            pre_transit_bike_max_confidence=settings.resolver.get("pre_transit_bike_max_confidence", 0.75),
        )
        expected.extend(str(row["ground_truth"]) for row in user_records)
        movement_predictions.extend(str(row["movement"]) for row in user_records)
        temporal_predictions.extend(temporal_modes)
        transit_predictions.extend(str(row["transit_decision"]["final_mode"]) for row in user_records)
        final_predictions.extend(final_modes)

    stages = {
        "movement": _metrics(expected, movement_predictions),
        "temporal": _metrics(expected, temporal_predictions),
        "transit": _metrics(expected, transit_predictions),
        "final": _metrics(expected, final_predictions),
    }
    baseline = float(stages["movement"]["macro_f1"])
    result = {
        "status": "PASS",
        "policy": "Ground Truth is read only after Movement inference; it is never passed to feature, model, temporal or transit code.",
        "split": split,
        "user_count": len({key.split(":", 1)[0] for key in records_by_sequence}),
        "transit_applicability_counts": dict(sorted(applicability.items())),
        "stages": stages,
        "macro_f1_delta_vs_movement": {
            name: float(metrics["macro_f1"]) - baseline for name, metrics in stages.items()
        },
    }
    output = Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
