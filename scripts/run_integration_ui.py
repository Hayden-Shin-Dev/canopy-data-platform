"""Run a dependency-free local UI for the Canopy GPS replay and integration status."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Lock, Thread
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from src.ktdb.schema import MODEL_FEATURES


HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Canopy Integration Local Test</title>
<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}section{border:1px solid #ddd;padding:1rem;margin:1rem 0;border-radius:6px}button{margin:.2rem;padding:.4rem .8rem}pre{white-space:pre-wrap;background:#f6f6f6;padding:.7rem}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:.3rem;text-align:left;font-size:.9rem}</style>
</head><body><h1>Canopy Integration Local Test</h1>
<section><label>Fixture <select id="fixture"></select></label> <label>Speed <select id="speed"><option>instant</option><option>1</option><option>5</option><option>10</option><option>30</option></select></label><button onclick="start()">Start</button><button onclick="post('/api/pause')">Pause</button><button onclick="post('/api/resume')">Resume</button><button onclick="post('/api/stop')">Stop</button><p id="status">WAITING</p></section>
<section><h2>GPS Replay</h2><pre id="replay">-</pre><table><thead><tr><th>sequence</th><th>timestamp</th><th>latitude</th><th>longitude</th><th>accuracy</th><th>speed</th><th>accepted</th><th>reason</th></tr></thead><tbody id="events"></tbody></table></section>
<section><h2>Window / GeoLife</h2><pre id="window">WAITING</pre></section>
<section><h2>Transit Context</h2><pre id="transit">WAITING</pre></section>
<section><h2>KTDB Expected Behaviour</h2><p>필수 KTDB MODEL_FEATURES를 JSON으로 입력한 뒤 Start를 누릅니다.</p><textarea id="expectedInput" rows="5" cols="100" placeholder='{"weekday": "weekday", "departure_hour": 8, ...}'></textarea><pre id="expected">WAITING</pre></section>
<section><h2>Emission / Full Pipeline</h2><pre id="pipeline">WAITING</pre></section>
<section><h2>Raw Debug</h2><pre id="raw">-</pre></section>
<script>
async function json(url, options){const r=await fetch(url,options);return await r.json()}
async function post(url){await json(url,{method:'POST'});}
async function start(){let expected_features=null;const text=document.getElementById('expectedInput').value.trim();if(text){expected_features=JSON.parse(text)}await json('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fixture:document.getElementById('fixture').value,speed:document.getElementById('speed').value,expected_features})});}
async function refresh(){const s=await json('/api/status');document.getElementById('status').textContent=s.status;document.getElementById('replay').textContent=JSON.stringify(s.replay,null,2);document.getElementById('window').textContent=JSON.stringify(s.pipeline.window||s.pipeline.error||s.pipeline.status||'WAITING',null,2);document.getElementById('transit').textContent=JSON.stringify(s.pipeline.transit_context||'WAITING',null,2);document.getElementById('expected').textContent=JSON.stringify(s.pipeline.expected_behaviour||s.pipeline.expected||'WAITING',null,2);document.getElementById('pipeline').textContent=JSON.stringify(s.pipeline,null,2);document.getElementById('raw').textContent=JSON.stringify(s.raw_debug,null,2);document.getElementById('events').innerHTML=(s.events||[]).map(e=>`<tr><td>${e.sequence??''}</td><td>${e.timestamp??''}</td><td>${e.latitude??''}</td><td>${e.longitude??''}</td><td>${e.horizontal_accuracy_m??''}</td><td>${e.speed_mps??''}</td><td>${e.accepted}</td><td>${(e.reasons||[]).join(',')}</td></tr>`).join('');}
async function init(){const f=await json('/api/fixtures');document.getElementById('fixture').innerHTML=f.map(x=>`<option>${x}</option>`).join('');refresh();setInterval(refresh,1000)} init();
</script></body></html>"""


class Runtime:
    def __init__(self) -> None:
        self.lock = Lock()
        self.status = "WAITING"
        self.engine: ReplayEngine | None = None
        self.thread: Thread | None = None
        self.fixture: str | None = None
        self.replay: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []
        self.pipeline: dict[str, Any] = {}
        self.expected_features: dict[str, object] | None = None

    def start(self, fixture: str, speed: str, expected_features: dict[str, object] | None = None) -> None:
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise RuntimeError("a replay is already running")
            path = _fixture_path(fixture)
            rows = read_replay_csv(path)
            self.engine = ReplayEngine(speed=speed if speed == "instant" else int(speed))
            self.fixture = path.name
            self.status = "RUNNING"
            self.replay = {"fixture": path.name, "speed": speed}
            self.events = []
            self.pipeline = {"status": "WAITING"}
            self.expected_features = expected_features
            self.thread = Thread(target=self._run, args=(rows,), daemon=True)
            self.thread.start()

    def _run(self, rows: list[dict[str, Any]]) -> None:
        assert self.engine is not None
        result = self.engine.stream(rows, on_update=self._on_update)
        with self.lock:
            self.replay.update({"status": result.status, "accepted": sum(item.decision.accepted for item in result.updates), "rejected": sum(not item.decision.accepted for item in result.updates)})
            stopped = result.status == "STOPPED"
            if stopped:
                self.status = "STOPPED"
                self.pipeline = {"status": "WAITING", "reason": "replay stopped before final processing"}
                return
            self.status = "PROCESSING"
            session = result.session
        try:
            session = self.engine.ingestor.stop_trip(session.trip_id)
            if self.expected_features is None:
                raise _WaitingForInput("KTDB Expected Behaviour inputs are required before final processing")
            missing = sorted(set(MODEL_FEATURES) - set(self.expected_features))
            if missing:
                raise _WaitingForInput(f"KTDB Expected Behaviour inputs missing: {missing}")
            references = TransitRuntimeReferences.from_directory()
            pipeline = run_full_pipeline(
                session.events,
                self.expected_features,
                references=references,
                geolife_model_path=ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib",
                ktdb_model_path=ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl",
                factors_csv=ROOT / "data/processed/emission_factors/emission_factors_2026.csv",
            )
            if pipeline.get("status") == "PASS":
                self.engine.ingestor.complete_trip(session.trip_id, pipeline)
            with self.lock:
                self.pipeline = pipeline
                self.status = str(pipeline.get("status", "FAIL"))
                return
        except _WaitingForInput as error:
            with self.lock:
                self.pipeline = {"status": "WAITING", "reason": str(error), "accepted_event_count": len(session.events)}
                self.status = "WAITING"
        except Exception as error:
            with self.lock:
                self.pipeline = {"status": "FAIL", "reason": str(error), "accepted_event_count": len(session.events)}
                self.status = "FAIL"

    def _on_update(self, update) -> None:
        event = update.decision.event
        item = {"index": update.index, "accepted": update.decision.accepted, "reasons": list(update.decision.reasons), "warnings": list(update.decision.warnings)}
        if event is not None:
            item.update(event.as_dict())
        with self.lock:
            self.events.append(item)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {"status": self.status, "fixture": self.fixture, "replay": dict(self.replay), "pipeline": self.pipeline, "events": list(self.events), "raw_debug": {"event_count": len(self.events), "accepted_count": sum(bool(event["accepted"]) for event in self.events), "rejected_count": sum(not bool(event["accepted"]) for event in self.events)}}


class _WaitingForInput(ValueError):
    """Pipeline cannot run until the user supplies required KTDB conditions."""


RUNTIME = Runtime()
FIXTURE_DIR = ROOT / "data/fixtures/integration"


def _fixture_path(name: str) -> Path:
    candidate = (FIXTURE_DIR / name).resolve()
    if candidate.parent != FIXTURE_DIR.resolve() or candidate.suffix.lower() != ".csv" or not candidate.is_file():
        raise ValueError("fixture must be an existing CSV under data/fixtures/integration")
    return candidate


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: object, content_type: str = "application/json") -> None:
        body = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, HTML, "text/html")
        elif path == "/api/fixtures":
            self._send(200, sorted(path.name for path in FIXTURE_DIR.glob("*.csv")))
        elif path == "/api/status":
            self._send(200, RUNTIME.snapshot())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/start":
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                expected = body.get("expected_features")
                if expected is not None and not isinstance(expected, dict):
                    raise ValueError("expected_features must be a JSON object")
                RUNTIME.start(str(body["fixture"]), str(body.get("speed", "instant")), expected)
            elif path == "/api/pause":
                assert RUNTIME.engine is not None
                RUNTIME.engine.pause()
                RUNTIME.status = "PAUSED"
            elif path == "/api/resume":
                assert RUNTIME.engine is not None
                RUNTIME.engine.resume()
                RUNTIME.status = "RUNNING"
            elif path == "/api/stop":
                assert RUNTIME.engine is not None
                RUNTIME.engine.stop()
            else:
                self._send(404, {"error": "not found"})
                return
            self._send(200, {"status": "ok"})
        except Exception as error:
            self._send(400, {"status": "FAIL", "error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Canopy Integration UI: http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
