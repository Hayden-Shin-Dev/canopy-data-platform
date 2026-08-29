"""Discovery and integrity checks for the frozen Seoul synthetic dataset.

The evaluator never writes under the dataset directory.  Predictions and
reports belong under ``reports/evaluation`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


REQUIRED_FILES = (
    "dataset_manifest.json",
    "freeze_manifest.json",
    "journey_manifest.csv",
    "reference_data_manifest.json",
    "validation_report.json",
)
FORBIDDEN_GPS_FIELDS = {
    "mode",
    "label",
    "ground_truth",
    "transport_mode",
    "scenario_type",
    "expected_mode",
    "synthetic_mode",
    "ground_truth_mode",
    "ground_truth_segment",
    "target",
}
GPS_FIELDS = {
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
}


@dataclass(frozen=True)
class FrozenDataset:
    """A discovered dataset root and its read-only manifest metadata."""

    root: Path
    dataset_manifest: dict[str, Any]
    freeze_manifest: dict[str, Any]
    validation_report: dict[str, Any]
    journey_manifest: pd.DataFrame

    @property
    def gps_dir(self) -> Path:
        return self.root / "gps"

    @property
    def ground_truth_dir(self) -> Path:
        return self.root / "ground_truth"

    @property
    def gps_files(self) -> list[Path]:
        return sorted(self.gps_dir.glob("*.csv"))

    @property
    def ground_truth_files(self) -> list[Path]:
        return sorted(self.ground_truth_dir.glob("*.json"))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return value


def discover_dataset(root: str | Path) -> FrozenDataset:
    """Find the single dataset_v1 root below ``root`` without copying files."""

    base = Path(root).resolve()
    candidates: list[Path] = []
    for manifest in base.rglob("dataset_manifest.json"):
        candidate = manifest.parent
        if all((candidate / name).is_file() for name in REQUIRED_FILES) and all(
            (candidate / name).is_dir() for name in ("gps", "ground_truth")
        ):
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError(f"expected one frozen dataset root, found {len(candidates)}: {candidates}")
    dataset_root = candidates[0]
    return FrozenDataset(
        root=dataset_root,
        dataset_manifest=_read_json(dataset_root / "dataset_manifest.json"),
        freeze_manifest=_read_json(dataset_root / "freeze_manifest.json"),
        validation_report=_read_json(dataset_root / "validation_report.json"),
        journey_manifest=pd.read_csv(dataset_root / "journey_manifest.csv"),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_frozen_dataset(dataset: FrozenDataset, *, verify_hashes: bool = True) -> dict[str, Any]:
    """Validate manifests, file counts, and optional freeze checksums."""

    manifest = dataset.dataset_manifest
    freeze = dataset.freeze_manifest
    validation = dataset.validation_report
    gps_files = dataset.gps_files
    truth_files = dataset.ground_truth_files
    expected_hashes = freeze.get("file_hashes", {})
    hash_results: dict[str, bool] = {}
    missing_hash_files: list[str] = []
    if verify_hashes and isinstance(expected_hashes, dict):
        for relative, expected in expected_hashes.items():
            path = dataset.root / str(relative)
            if not path.is_file():
                # The copied evaluation package intentionally contains only
                # GPS, Ground Truth, and top-level manifests. Optional
                # generator visualizations are not required for evaluation.
                missing_hash_files.append(str(relative))
                continue
            hash_results[str(relative)] = _sha256(path) == str(expected)
    frozen_status = freeze.get("status") or manifest.get("freeze", {}).get("status")
    checks = {
        "dataset_version": manifest.get("dataset_version") == "dataset_v1",
        "frozen": str(frozen_status or "").lower() == "frozen",
        "journey_count": int(manifest.get("journey_count", -1)) == 700 == len(dataset.journey_manifest),
        "gps_count": int(manifest.get("journey_count", -1)) == len(gps_files),
        "ground_truth_count": int(manifest.get("journey_count", -1)) == len(truth_files),
        "validation_report_passed": validation.get("status") == "passed" and int(validation.get("failed", 1)) == 0,
        "manifest_hashes": all(hash_results.values()) if hash_results else not verify_hashes,
    }
    return {
        "root": str(dataset.root),
        "dataset_version": manifest.get("dataset_version"),
        "frozen": frozen_status,
        "journey_count": len(dataset.journey_manifest),
        "gps_file_count": len(gps_files),
        "ground_truth_file_count": len(truth_files),
        "validation_status": validation.get("status"),
        "hashes_checked": len(hash_results),
        "hashes_passed": sum(hash_results.values()),
        "hashes_missing_optional": missing_hash_files,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def gps_leakage_fields(path: str | Path) -> set[str]:
    """Return forbidden label-like columns found in one GPS CSV."""

    columns = set(pd.read_csv(path, nrows=0).columns)
    return columns & FORBIDDEN_GPS_FIELDS


def validate_gps_schema(path: str | Path) -> dict[str, Any]:
    """Check the canonical iPhone GPS columns and reject label leakage."""

    columns = set(pd.read_csv(path, nrows=0).columns)
    missing = sorted(GPS_FIELDS - columns)
    forbidden = sorted(columns & FORBIDDEN_GPS_FIELDS)
    return {
        "path": str(path),
        "missing": missing,
        "forbidden": forbidden,
        "status": "PASS" if not missing and not forbidden else "FAIL",
    }


def iter_manifest_rows(dataset: FrozenDataset) -> Iterable[dict[str, Any]]:
    """Yield manifest rows with stable trip IDs and paths."""

    for row in dataset.journey_manifest.to_dict(orient="records"):
        trip_id = str(row["trip_id"])
        yield {
            **row,
            "trip_id": trip_id,
            "gps_path": dataset.gps_dir / f"{trip_id}.csv",
            "ground_truth_path": dataset.ground_truth_dir / f"{trip_id}.json",
        }
