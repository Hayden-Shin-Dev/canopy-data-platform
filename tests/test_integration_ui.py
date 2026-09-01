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

    assert "Baseline Preview" in module.IPHONE_HTML
    assert "Trip Detail" in module.IPHONE_HTML
    assert "developer-only" in module.IPHONE_HTML
    assert "openstreetmap.org" in module.MOBILE_APP_HTML
    assert "startTrip()" in module.MOBILE_APP_HTML
    assert 'class="screen active"' in module.MOBILE_APP_HTML
    assert "resultSegments" in module.MOBILE_APP_HTML
    assert "renderSegments" in module.MOBILE_APP_HTML
    assert "modeVisual" in module.MOBILE_APP_HTML
    assert "renderModeVisual" in module.MOBILE_APP_HTML
    assert 'id="reward"' in module.MOBILE_APP_HTML
    assert "결과 확인" in module.MOBILE_APP_HTML
    assert 'id="homeTokenBalance"' in module.MOBILE_APP_HTML
    assert "showReward" in module.MOBILE_APP_HTML
    assert "TOKEN_GRAMS_PER_TOKEN" in module.MOBILE_APP_HTML
    assert "tokenEarned" in module.MOBILE_APP_HTML
    assert 'id="mypage"' in module.MOBILE_APP_HTML
    assert 'class="bottom-nav"' in module.MOBILE_APP_HTML
    assert "navigateTab" in module.MOBILE_APP_HTML
    assert "AI-Hub Real GPS Replay" in module.MOBILE_APP_HTML
    assert 'id="aihubReplay"' in module.MOBILE_APP_HTML
    assert "runAIHubReplay" in module.MOBILE_APP_HTML

    assert module._fixture_path("insufficient_gps.csv").is_file()
    runtime.start("insufficient_gps.csv", "instant")
    for _ in range(30):
        if runtime.thread and not runtime.thread.is_alive():
            break
        time.sleep(0.01)
    snapshot = runtime.snapshot()

    assert snapshot["status"] == "WAITING"
    assert "KTDB Expected Behaviour inputs" in snapshot["pipeline"]["reason"]


def test_ui_accepts_repository_mock_input_without_ground_truth():
    module = _module()

    path = module._fixture_path("mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv")
    assert path == module.DEFAULT_MOCK
    rows = module.read_replay_csv(path)
    assert len(rows) == 433
    assert "ground_truth_mode" not in rows[0]


def test_ui_route_and_baseline_endpoints_use_real_local_inputs():
    module = _module()

    route = module._route_payload()
    baseline = module._baseline_payload()

    assert route["status"] == "READY"
    assert route["origin"]["label"].startswith("서울 영등포구")
    assert route["destination"]["label"].startswith("Microsoft Korea")
    assert baseline["status"] == "READY"
    assert set(baseline["probabilities"]) == {"walk", "bike", "car", "bus", "rail"}
    assert abs(sum(baseline["probabilities"].values()) - 1) < 1e-6


def test_aihub_manifest_exposes_test_case_metadata_without_raw_paths():
    module = _module()

    payload = module._aihub_manifest_payload()

    assert payload["status"] == "READY"
    assert len(payload["trajectories"]) == 25
    assert {row["ground_truth"] for row in payload["trajectories"]} == {"walk", "bike", "car", "bus", "rail"}
    assert all("gps_file" not in row and "label_file" not in row for row in payload["trajectories"])


def test_aihub_replay_requires_local_dataset_root_and_known_case():
    module = _module()

    try:
        module._run_aihub_replay("UNKNOWN", "C:/missing", "instant")
    except ValueError as error:
        assert "unknown AI-Hub replay id" in str(error)
    else:
        raise AssertionError("unknown replay id must be rejected")

    try:
        module._run_aihub_replay("WALK-01", "", "instant")
    except ValueError as error:
        assert "source_root" in str(error)
    else:
        raise AssertionError("missing source root must be rejected")


def test_ui_runs_existing_pipeline_for_repository_mock():
    module = _module()
    runtime = module.Runtime()
    runtime.start("mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv", "instant")
    for _ in range(300):
        if runtime.thread and not runtime.thread.is_alive():
            break
        time.sleep(0.02)

    snapshot = runtime.snapshot()
    assert snapshot["status"] == "PASS"
    assert snapshot["raw_debug"]["accepted_count"] == 433
    assert len(snapshot["window_predictions"]) == 18
    assert snapshot["pipeline"]["status"] == "PASS"
    assert snapshot["pipeline"]["actual_behaviour"]["mode_sequence"]
    assert snapshot["pipeline"]["actual_behaviour"]["segments"]
    assert snapshot["pipeline"]["co2"]["actual_co2e_g"] > 0
