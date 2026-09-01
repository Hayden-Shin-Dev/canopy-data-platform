"""Safe selection and loading of AI-Hub Test UID trajectories for replay."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


class ReplaySelectionError(ValueError):
    """Raised when a trajectory is not allowed in the real-GPS replay."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_split_manifest(path: str | Path) -> dict[str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    groups = payload.get("groups", [])
    return {str(item["user_id"]).zfill(8): str(item["split"]) for item in groups}


def validate_replay_uid(uid: str, split_manifest: dict[str, str]) -> str:
    normalized = str(uid).zfill(8)
    split = split_manifest.get(normalized)
    if split is None:
        raise ReplaySelectionError(f"UNKNOWN_UID: {normalized}")
    if split != "test":
        raise ReplaySelectionError(f"REPLAY_REJECTED_{split.upper()}_UID: {normalized}")
    return normalized


def _raw_index(source_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in sorted(source_root.rglob("TMC-GPS-*.csv")):
        index[path.stem] = path
    return index


def select_test_trajectories(
    windows_csv: str | Path,
    split_manifest: str | Path,
    source_root: str | Path,
    output_manifest: str | Path,
    *,
    per_class: int = 5,
) -> dict[str, object]:
    """Select deterministic, quality-filtered Test trajectories without copying raw GPS."""

    if per_class < 1:
        raise ValueError("per_class must be positive")
    split_map = load_split_manifest(split_manifest)
    source_root_path = Path(source_root).resolve()
    raw_paths = _raw_index(source_root_path)
    candidates: list[dict[str, object]] = []
    with Path(windows_csv).open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if str(row.get("split", "")).lower() != "test":
                continue
            mode = str(row.get("canonical_mode", ""))
            if mode not in {"walk", "bike", "car", "bus", "rail"}:
                continue
            uid = validate_replay_uid(str(row.get("user_id", "")), split_map)
            trajectory_id = str(row.get("trajectory_id", ""))
            path = raw_paths.get(trajectory_id)
            if path is None:
                continue
            try:
                point_count = int(float(row.get("point_count", 0)))
                duration = float(row.get("observed_duration_sec", 0))
                invalid = int(float(row.get("invalid_coordinate_count", 0)))
                missing = int(float(row.get("missing_coordinate_count", 0)))
            except (TypeError, ValueError):
                continue
            if point_count < 2 or duration < 45 or invalid or missing:
                continue
            candidates.append(
                {
                    "uid": uid,
                    "trajectory_id": trajectory_id,
                    "ground_truth": mode,
                    # Keep the manifest portable: AI-Hub directory names are
                    # localized, while the trajectory filename is stable.
                    "gps_file": path.name,
                    "point_count": point_count,
                    "duration_seconds": duration,
                    "start_timestamp": str(row.get("window_start", "")),
                    "end_timestamp": str(row.get("window_end", "")),
                    "source_class": str(row.get("source_class", "")),
                    "file_sha256": _sha256(path),
                }
            )
    selected: list[dict[str, object]] = []
    for mode in ("walk", "bike", "car", "bus", "rail"):
        mode_rows = sorted(
            (row for row in candidates if row["ground_truth"] == mode),
            key=lambda row: (str(row["uid"]), str(row["start_timestamp"]), str(row["trajectory_id"])),
        )
        groups: list[dict[str, object]] = []
        for left, middle, right in zip(mode_rows, mode_rows[1:], mode_rows[2:]):
            if not (left["uid"] == middle["uid"] == right["uid"]):
                continue
            try:
                left_end = datetime.fromisoformat(str(left["end_timestamp"]))
                middle_start = datetime.fromisoformat(str(middle["start_timestamp"]))
                middle_end = datetime.fromisoformat(str(middle["end_timestamp"]))
                right_start = datetime.fromisoformat(str(right["start_timestamp"]))
            except ValueError:
                continue
            if not (0 <= (middle_start - left_end).total_seconds() <= 5 and 0 <= (right_start - middle_end).total_seconds() <= 5):
                continue
            groups.append(
                {
                    "uid": left["uid"],
                    "trajectory_id": f"{left['trajectory_id']}__{middle['trajectory_id']}__{right['trajectory_id']}",
                    "ground_truth": mode,
                    "gps_file": [left["gps_file"], middle["gps_file"], right["gps_file"]],
                    "point_count": int(left["point_count"]) + int(middle["point_count"]) + int(right["point_count"]),
                    "duration_seconds": (right_start - datetime.fromisoformat(str(left["start_timestamp"]))).total_seconds() + float(right["duration_seconds"]),
                    "start_timestamp": left["start_timestamp"],
                    "end_timestamp": right["end_timestamp"],
                    "source_class": left["source_class"],
                    "file_sha256": [left["file_sha256"], middle["file_sha256"], right["file_sha256"]],
                }
            )
        for index, row in enumerate(groups[:per_class], start=1):
            selected.append({"replay_id": f"{mode.upper()}-{index:02d}", "selection_rule": "test_uid;quality;adjacent_120s_group sort", **row})
    counts = {mode: sum(row["ground_truth"] == mode for row in selected) for mode in ("walk", "bike", "car", "bus", "rail")}
    if any(value < per_class for value in counts.values()):
        raise ReplaySelectionError(f"insufficient usable Test trajectories: {counts}")
    result = {
        "schema_version": "aihub-replay-manifest-v1",
        "source_root": "external AI-Hub dataset root (pass to the loader)",
        "split_manifest": Path(split_manifest).name,
        "split_manifest_sha256": _sha256(Path(split_manifest)),
        "selection_rule": "test_uid;quality;adjacent_120s_group sort",
        "per_class": per_class,
        "trajectory_count": len(selected),
        "class_counts": counts,
        "ground_truth_for_evaluation_only": True,
        "trajectories": selected,
    }
    destination = Path(output_manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def iter_aihub_payloads(entry: dict[str, object], *, source_root: str | Path | None = None) -> Iterator[dict[str, Any]]:
    """Convert raw AI-Hub GPS rows to the canonical label-free replay contract."""

    raw_files = entry["gps_file"] if isinstance(entry["gps_file"], list) else [entry["gps_file"]]
    paths: list[Path] = []
    for raw_file in raw_files:
        path = Path(str(raw_file))
        if source_root is not None and not path.is_absolute():
            path = Path(source_root) / path
            if not path.is_file():
                matches = sorted(Path(source_root).rglob(path.name))
                if matches:
                    path = matches[0]
        paths.append(path)
    uid = str(entry["uid"])
    trip_id = f"aihub-{uid}-{entry['trajectory_id']}"
    sequence = 0
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if set(reader.fieldnames or ()) != {"timestamp", "latitude", "longitude", "accuracy", "altitude"}:
                raise ReplaySelectionError(f"unexpected AI-Hub GPS header: {path}")
            for row in reader:
                try:
                    timestamp = datetime.fromtimestamp(int(row["timestamp"]) / 1000, tz=UTC).isoformat().replace("+00:00", "Z")
                    latitude = float(row["latitude"])
                    longitude = float(row["longitude"])
                    accuracy = float(row["accuracy"]) if str(row.get("accuracy", "")).strip() else -1.0
                    altitude = float(row["altitude"]) if str(row.get("altitude", "")).strip() else -9999.0
                except (TypeError, ValueError, OverflowError, OSError):
                    continue
                yield {
                    "schema_version": "1.0",
                    "trip_id": trip_id,
                    "device_id": f"aihub-{uid}",
                    "sequence": sequence,
                    "timestamp": timestamp,
                    "latitude": latitude,
                    "longitude": longitude,
                    "horizontal_accuracy_m": accuracy,
                    "altitude_m": altitude,
                    "vertical_accuracy_m": -1.0,
                    "speed_mps": -1.0,
                    "course_deg": -1.0,
                    "source": "aihub_real_gps",
                    "is_simulated": False,
                }
                sequence += 1
