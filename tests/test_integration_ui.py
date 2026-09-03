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
    assert "/ui/app.js" in module.MOBILE_APP_HTML
    static_js = (Path(__file__).resolve().parents[1] / "src/integration/ui/app.js").read_text(encoding="utf-8")
    assert "openstreetmap.org" in static_js
    assert "/ui/styles.css" in module.MOBILE_APP_HTML
    static_html = module.MOBILE_APP_HTML
    static_css = (Path(__file__).resolve().parents[1] / "src/integration/ui/styles.css").read_text(encoding="utf-8")
    assert 'data-testid="iphone-frame"' in static_html
    for marker in ('id="result-segments"', 'id="result-token"', 'id="profile"', 'class="bottom-nav"'):
        assert marker in static_html
    for screen in ("home", "plan", "start", "active", "complete", "profile", "developer"):
        assert f'id="{screen}"' in static_html
    assert "/assets/canopy-ui/home-landscape.png" in static_html
    for asset in (
        "journey-start-backdrop.png",
        "journey-start-sprite.png",
        "journey-complete-confetti.png",
        "journey-complete-celebration-sprite.png",
    ):
        assert f"/assets/canopy-ui/{asset}" in static_css
    assert "startTrip" in static_js
    assert "renderResult" in static_js

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
