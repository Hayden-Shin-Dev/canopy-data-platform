"""Run a non-destructive readiness/smoke check for the official AI-Hub model.

The official package is external to this repository. This command never loads
or modifies the Docker image and never fabricates missing sensor values. When
Docker is unavailable it writes a reproducible BLOCKED report instead of a
false PASS.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

from src.mobility_v4.contracts import OFFICIAL_CONTRACT


def _docker_status() -> dict[str, object]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{json .ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": type(exc).__name__}
    return {
        "available": proc.returncode == 0,
        "server_version": proc.stdout.strip() if proc.returncode == 0 else None,
        "error": proc.stderr.strip() if proc.returncode else None,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def _checkpoint_status(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            result.update(
                {
                    "archive_readable": True,
                    "has_data_pickle": "archive/data.pkl" in names,
                    "has_version": "archive/version" in names,
                    "state_dict_fc_weight": "model.fc.weight" in archive.read("archive/data.pkl").decode("latin1", "ignore"),
                }
            )
    except (OSError, zipfile.BadZipFile) as exc:
        result.update({"archive_readable": False, "error": str(exc)})
    return result


def build_report(official_root: Path) -> dict[str, object]:
    checkpoint = official_root / "학습모델파일" / "last.chk"
    docker = _docker_status()
    checkpoint_status = _checkpoint_status(checkpoint)
    runnable = bool(docker["available"] and checkpoint_status.get("archive_readable"))
    return {
        "status": "READY_FOR_DOCKER_REPRODUCTION" if runnable else "BLOCKED",
        "reason": None if runnable else "Docker daemon or official checkpoint runtime is unavailable",
        "official_contract": OFFICIAL_CONTRACT,
        "checkpoint": checkpoint_status,
        "docker": docker,
        "inference": {
            "executed": False,
            "input_shape": None,
            "output_shape": None,
            "predicted_class": None,
            "latency_ms": None,
        },
        "policy": {
            "missing_modalities_synthesized": False,
            "production_model_changed": False,
            "test_used_for_tuning": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--official-root",
        type=Path,
        default=(Path(os.environ["AIHUB_OFFICIAL_ROOT"]) if os.environ.get("AIHUB_OFFICIAL_ROOT") else None),
        help="external AI-Hub package root",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.official_root is None:
        parser.error("--official-root or AIHUB_OFFICIAL_ROOT is required")
    report = build_report(args.official_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "READY_FOR_DOCKER_REPRODUCTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
