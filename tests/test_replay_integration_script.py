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
