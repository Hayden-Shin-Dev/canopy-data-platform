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
    assert "/ui/styles.css" in module.MOBILE_APP_HTML
    assert "/ui/app.js" in module.MOBILE_APP_HTML
    assert "여정 시작하기" in module.MOBILE_APP_HTML
    assert 'id="result-segments"' in module.MOBILE_APP_HTML
    assert 'id="result-token"' in module.MOBILE_APP_HTML
    assert 'id="profile"' in module.MOBILE_APP_HTML
    assert 'class="bottom-nav"' in module.MOBILE_APP_HTML
    for screen in ("home", "plan", "start", "active", "complete", "profile", "developer"):
        assert f'id="{screen}"' in module.MOBILE_APP_HTML
    assert "/assets/canopy-ui/home-landscape.png" in module.MOBILE_APP_HTML
    assert "/assets/canopy-ui/journey-start.png" in module.MOBILE_APP_HTML
    assert "/assets/canopy-ui/journey-complete.png" in module.MOBILE_APP_HTML
    assert "AI-Hub Real GPS Replay" in module.MOBILE_APP_HTML
    assert 'id="aihub-replay"' in module.MOBILE_APP_HTML

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
    assert route["distance_km"] > 0
    assert len(route["polyline"]) > 2
    assert baseline["status"] == "READY"
    assert set(baseline["probabilities"]) == {"walk", "bike", "car", "bus", "rail"}
    assert abs(sum(baseline["probabilities"].values()) - 1) < 1e-6
    assert baseline["distance_km"] > 0
    assert baseline["duration_sec"] > 0
    assert baseline["expected_co2e_g"] > 0


def test_ui_static_files_keep_the_five_screen_flow_and_real_data_hooks():
    root = Path(__file__).resolve().parents[1]
    javascript = (root / "src/integration/ui/app.js").read_text(encoding="utf-8")
    stylesheet = (root / "src/integration/ui/styles.css").read_text(encoding="utf-8")

    for hook in ("/api/baseline", "/api/route", "/api/start", "/api/status", "/api/stop"):
        assert hook in javascript
    assert "ground_truth_mode" not in javascript.lower()
    assert "393px" in stylesheet
    assert "852px" in stylesheet


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
