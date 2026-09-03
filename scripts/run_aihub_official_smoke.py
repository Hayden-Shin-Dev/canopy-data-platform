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


def _docker_status(image: str = "nia56:latest") -> dict[str, object]:
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
    result: dict[str, object] = {
        "available": proc.returncode == 0,
        "server_version": proc.stdout.strip() if proc.returncode == 0 else None,
        "error": proc.stderr.strip() if proc.returncode else None,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "image": image,
    }
    if proc.returncode != 0:
        return result

    image_proc = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}} {{.Size}}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    result["image_available"] = image_proc.returncode == 0
    result["image_inspect"] = image_proc.stdout.strip() if image_proc.returncode == 0 else image_proc.stderr.strip()

    # The official image ships a Python 3.9 torch39 environment. This is a
    # runtime-only check; it does not run inference or alter the image.
    if image_proc.returncode == 0:
        cpu_proc = subprocess.run(
            [
                "docker", "run", "--rm", "--entrypoint",
                "/opt/conda/envs/torch39/bin/python", image, "-c",
                "import torch,sys; print(sys.version.split()[0]); print(torch.__version__); print(torch.cuda.is_available())",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        result["cpu_runtime"] = {
            "ok": cpu_proc.returncode == 0,
            "stdout": cpu_proc.stdout.strip(),
            "stderr": cpu_proc.stderr.strip(),
        }
        gpu_proc = subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all", "--entrypoint", "/bin/true", image],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        result["gpu_runtime"] = {
            "ok": gpu_proc.returncode == 0,
            "stdout": gpu_proc.stdout.strip(),
            "stderr": gpu_proc.stderr.strip(),
        }
    return result


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


def _input_status(data_root: Path | None) -> dict[str, object]:
    """Check for the four raw sensor trees required by official preprocessing."""
    if data_root is None:
        return {
            "provided": False,
            "full_modality_available": False,
            "missing_modalities": ["gps", "imu", "ap", "bts"],
        }
    modality_dirs = {
        "ap": list(data_root.rglob("1.AP")) if data_root.exists() else [],
        "bts": list(data_root.rglob("2.BTS")) if data_root.exists() else [],
        "gps": list(data_root.rglob("3.GPS")) if data_root.exists() else [],
        "imu": list(data_root.rglob("4.IMU")) if data_root.exists() else [],
    }
    # The public release also ships a flattened GPS-only tree named
    # ``TS_...GPS_XX...``. Record it as observed data, but keep it distinct
    # from the official ``1.AP/2.BTS/3.GPS/4.IMU`` layout.
    observed = {
        name: bool(paths)
        for name, paths in modality_dirs.items()
    }
    if not observed["gps"]:
        observed["gps"] = any(
            path.is_dir() and "GPS" in path.name.upper()
            for path in data_root.rglob("*")
        )
    present = [name for name, found in observed.items() if found]
    missing = [name for name in modality_dirs if name not in present]
    return {
        "provided": True,
        "root": str(data_root),
        "present_modalities": present,
        "missing_modalities": missing,
        "official_tree_present": [name for name, paths in modality_dirs.items() if paths],
        "format_compatible": not missing and all(modality_dirs.values()),
        "full_modality_available": not missing,
    }


def build_report(
    official_root: Path,
    image: str = "nia56:latest",
    data_root: Path | None = None,
) -> dict[str, object]:
    checkpoint = official_root / "학습모델파일" / "last.chk"
    if not checkpoint.is_file():
        # Korean archive directory names vary with Windows locale/code page.
        candidates = list(official_root.rglob("last.chk")) if official_root.exists() else []
        checkpoint = candidates[0] if candidates else checkpoint
    docker = _docker_status(image)
    checkpoint_status = _checkpoint_status(checkpoint)
    input_status = _input_status(data_root)
    runnable = bool(
        docker["available"]
        and docker.get("image_available")
        and checkpoint_status.get("archive_readable")
        and input_status["full_modality_available"]
    )
    if not input_status["full_modality_available"]:
        reason = "Official preprocessing requires raw GPS, IMU, AP, and BTS files; missing modalities were not synthesized"
    elif not docker["available"] or not docker.get("image_available"):
        reason = "Docker daemon or official image is unavailable"
    elif not checkpoint_status.get("archive_readable"):
        reason = "Official checkpoint is unavailable or unreadable"
    else:
        reason = None
    return {
        "status": "READY_FOR_DOCKER_REPRODUCTION" if runnable else "BLOCKED",
        "reason": reason,
        "official_contract": OFFICIAL_CONTRACT,
        "checkpoint": checkpoint_status,
        "input_data": input_status,
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
    parser.add_argument("--image", default="nia56:latest", help="loaded official Docker image tag")
    parser.add_argument("--data-root", type=Path, help="external raw data root with official sensor trees")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.official_root is None:
        parser.error("--official-root or AIHUB_OFFICIAL_ROOT is required")
    report = build_report(args.official_root, image=args.image, data_root=args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "READY_FOR_DOCKER_REPRODUCTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
