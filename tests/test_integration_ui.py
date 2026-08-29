import importlib.util
from pathlib import Path
import time


def _module():
    path = Path(__file__).resolve().parents[1] / "scripts/run_integration_ui.py"
    spec = importlib.util.spec_from_file_location("run_integration_ui", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ui_runtime_lists_fixture_and_reports_waiting_without_fabricated_inputs():
    module = _module()
    runtime = module.Runtime()

    assert module._fixture_path("insufficient_gps.csv").is_file()
    runtime.start("insufficient_gps.csv", "instant")
    for _ in range(30):
        if runtime.thread and not runtime.thread.is_alive():
            break
        time.sleep(0.01)
    snapshot = runtime.snapshot()

    assert snapshot["status"] == "WAITING"
    assert "KTDB Expected Behaviour inputs" in snapshot["pipeline"]["reason"]
