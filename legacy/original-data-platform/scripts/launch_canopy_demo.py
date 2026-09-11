"""Launch the local Canopy demo server and open it in the default browser."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        # The EXE is intentionally kept next to the repository so the large
        # model/data directories stay external and are not duplicated.
        location = Path(sys.executable).resolve().parent
        if (location / "scripts" / "run_integration_ui.py").is_file():
            return location
        if (location.parent / "scripts" / "run_integration_ui.py").is_file():
            return location.parent
        return location
    return Path(__file__).resolve().parents[1]


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "Canopy Demo", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def server_is_ready() -> bool:
    try:
        with urllib.request.urlopen(URL, timeout=0.6) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def python_command() -> str | None:
    if not getattr(sys, "frozen", False):
        return sys.executable
    return shutil.which("python") or shutil.which("py")


def main() -> int:
    root = project_root()
    script = root / "scripts" / "run_integration_ui.py"
    if not script.is_file():
        show_error(f"Canopy 프로젝트를 찾지 못했습니다.\n실행 파일 위치: {root}")
        return 1

    # Opening a second EXE should reuse an already running demo instead of
    # creating a second server on the same port.
    if server_is_ready():
        webbrowser.open(URL)
        return 0

    command = python_command()
    if command is None:
        show_error("Python이 설치되어 있지 않습니다. 프로젝트 실행 환경을 먼저 설치해주세요.")
        return 1

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [command, str(script), "--host", HOST, "--port", str(PORT)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                show_error("Canopy 데모 서버가 시작되지 않았습니다.\nrun_canopy_app.bat로 오류 로그를 확인해주세요.")
                return process.returncode or 1
            if server_is_ready():
                webbrowser.open(URL)
                return process.wait()
            time.sleep(0.25)
        show_error("Canopy 데모 서버 시작 시간이 초과됐습니다.")
        return 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
