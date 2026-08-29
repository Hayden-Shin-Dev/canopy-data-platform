import json
import subprocess
import sys
from pathlib import Path


def test_replay_script_reports_event_decisions():
    root = Path(__file__).resolve().parents[1]
    fixture = root / "data/fixtures/integration/quality_edge_cases.csv"
    completed = subprocess.run([sys.executable, "scripts/replay_integration.py", str(fixture)], cwd=root, capture_output=True, text=True, check=True)
    output = json.loads(completed.stdout)

    assert output["replay_status"] == "STREAMED"
    assert len(output["updates"]) == 4
    assert output["session"]["rejected_event_count"] == 2


def test_replay_script_uses_label_free_mock_by_default():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "scripts/replay_integration.py", "--speed", "instant"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    output = json.loads(completed.stdout)

    assert output["session"]["trip_id"] == "trip-ydp-gwanghwamun-001"
    assert output["session"]["accepted_event_count"] == 433
    assert output["session"]["rejected_event_count"] == 0
