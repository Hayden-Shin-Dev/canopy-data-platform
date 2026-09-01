"""Validate the AI-Hub split, model artifact contract, and release metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from src.aihub.config import CANOPY_MODES
from src.aihub.features import AIHUB_FEATURE_COLUMNS


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(
    dataset_csv: str | Path,
    manifest_json: str | Path,
    artifact_path: str | Path,
    *,
    expected_window_seconds: int = 60,
) -> dict[str, object]:
    frame = pd.read_csv(dataset_csv, dtype={"user_id": "string"})
    split_users = {name: set(frame.loc[frame["split"] == name, "user_id"].astype(str)) for name in ("train", "validation", "test")}
    overlap = {f"{left}_{right}": len(split_users[left] & split_users[right]) for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))}
    manifest_hash = sha256(manifest_json)
    bundle = joblib.load(artifact_path)
    checks = {
        "all_classes_in_split": all(set(CANOPY_MODES) <= set(frame.loc[frame["split"] == name, "canonical_mode"].astype(str)) for name in split_users),
        "user_overlap_zero": all(value == 0 for value in overlap.values()),
        "feature_contract": list(bundle.get("feature_columns", ())) == list(AIHUB_FEATURE_COLUMNS),
        "dataset_hash_matches": bundle.get("dataset_sha256") == sha256(dataset_csv),
        "manifest_hash_matches": bundle.get("split_manifest_sha256") == manifest_hash,
        "window_contract": bundle.get("window_duration_seconds") == expected_window_seconds,
    }
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "user_overlap": overlap, "rows": {name: int((frame["split"] == name).sum()) for name in split_users}}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_csv")
    parser.add_argument("manifest_json")
    parser.add_argument("artifact_path")
    parser.add_argument("--window-seconds", type=int, default=60)
    args = parser.parse_args()
    result = validate(
        args.dataset_csv,
        args.manifest_json,
        args.artifact_path,
        expected_window_seconds=args.window_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
