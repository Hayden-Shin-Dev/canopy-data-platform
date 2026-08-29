"""Run a dependency-free local UI for the Canopy GPS replay and integration status."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Lock, Thread
from typing import Any
from urllib.parse import urlparse

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integration.geolife_adapter import infer_windows
from src.integration.pipeline import TransitRuntimeReferences, run_full_pipeline
from src.integration.replay import ReplayEngine, read_replay_csv
from src.ktdb.schema import MODEL_FEATURES


MOCK_DIR = ROOT / "mock"
DEFAULT_MOCK = MOCK_DIR / "canopy_iphone_mock_yeongdeungpo_to_microsoft.csv"
DEFAULT_KTDB_SAMPLE = ROOT / "data/processed/population_baseline/ktdb/01_population_model_training_all.csv"


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


IPHONE_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Canopy</title>
<style>body{max-width:430px;margin:0 auto;padding:16px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f6f8;color:#17202a}h1{letter-spacing:.08em}section{background:#fff;border:1px solid #e1e5e8;border-radius:14px;padding:14px;margin:12px 0}button,select{padding:8px;margin:3px;border:1px solid #cbd3da;border-radius:8px;background:#fff}.primary{background:#1d7a55;color:#fff}.metric{display:flex;justify-content:space-between;border-top:1px solid #edf0f2;padding:8px 0}svg{width:100%;height:180px;background:#eef5f1;border-radius:10px}.developer-only{display:none}pre{white-space:pre-wrap;overflow:auto;background:#f6f7f8;padding:8px;border-radius:8px;font-size:.75rem}table{border-collapse:collapse;width:100%;display:block;overflow:auto;max-height:280px}td,th{border:1px solid #e1e5e8;padding:4px;font-size:.72rem;white-space:nowrap}</style></head>
<body><h1>CANOPY</h1><p>친환경 이동 분석</p>
<section><h2>오늘의 이동</h2><div class="metric"><span>탄소 절감</span><strong id="homeReduction">0 g</strong></div><div class="metric"><span>이동 거리</span><strong id="homeDistance">0 km</strong></div><button class="primary" onclick="start()">이동 시작</button></section>
<section><h2>Test Mode</h2><label>입력 <select id="fixture"></select></label><label>Replay <select id="speed"><option>instant</option><option>1</option><option>5</option><option>10</option><option>30</option></select></label><label>화면 <select id="viewMode" onchange="toggleDeveloper()"><option value="user">User Mode</option><option value="developer">Developer Mode</option></select></label><div><button onclick="start()">Start</button><button onclick="post('/api/pause')">Pause</button><button onclick="post('/api/resume')">Resume</button><button onclick="post('/api/stop')">Stop</button></div><p id="status">WAITING</p></section>
<section><h2>Active Trip</h2><p id="tripState">이동을 시작하면 현재 GPS를 표시합니다.</p><svg viewBox="0 0 100 100"><polyline id="path" fill="none" stroke="#1d7a55" stroke-width="1.5" points=""/></svg><pre id="replay">-</pre><table><thead><tr><th>sequence</th><th>timestamp</th><th>latitude</th><th>longitude</th><th>accuracy</th><th>accepted</th></tr></thead><tbody id="events"></tbody></table></section>
<section><h2>Trip Result</h2><div class="metric"><span>실제 감지 이동수단</span><strong id="actualMode">-</strong></div><div class="metric"><span>예상 이동수단</span><strong id="expectedMode">-</strong></div><div class="metric"><span>실제 배출량</span><span id="actualCo2">-</span></div><div class="metric"><span>예상 배출량</span><span id="expectedCo2">-</span></div><div class="metric"><span>절감량</span><span id="reduction">-</span></div></section>
<section class="developer-only" id="developer"><h2>Developer Mode</h2><h3>120s GeoLife Windows</h3><pre id="windows">WAITING</pre><h3>Transit Context</h3><pre id="transit">WAITING</pre><h3>KTDB Expected Behaviour</h3><p>기존 KTDB feature JSON은 Developer Mode에서만 입력합니다.</p><textarea id="expectedInput" rows="5" style="width:100%" placeholder='{"weekday": "weekday", "departure_hour": 8, ...}'></textarea><pre id="expected">WAITING</pre><h3>Full Pipeline / Raw Debug</h3><pre id="pipeline">WAITING</pre><pre id="raw">-</pre></section>
<script>
async function json(url,options){const r=await fetch(url,options);return await r.json()} async function post(url){await json(url,{method:'POST'})} function toggleDeveloper(){document.getElementById('developer').style.display=document.getElementById('viewMode').value==='developer'?'block':'none'}
async function start(){let expected_features=null;if(document.getElementById('viewMode').value==='developer'){const text=document.getElementById('expectedInput').value.trim();if(text)expected_features=JSON.parse(text)}await json('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fixture:document.getElementById('fixture').value,speed:document.getElementById('speed').value,expected_features,view_mode:document.getElementById('viewMode').value})})}
function drawMap(events){const v=(events||[]).filter(e=>e.accepted&&e.latitude!==undefined);if(!v.length)return;const a=v.map(e=>+e.latitude),o=v.map(e=>+e.longitude),la=Math.min(...a),ha=Math.max(...a),lo=Math.min(...o),ho=Math.max(...o),dy=ha-la||1e-6,dx=ho-lo||1e-6;document.getElementById('path').setAttribute('points',v.map(e=>`${((+e.longitude-lo)/dx*90+5).toFixed(2)},${(95-(+e.latitude-la)/dy*90).toFixed(2)}`).join(' '))}
async function refresh(){const s=await json('/api/status'),p=s.pipeline||{};document.getElementById('status').textContent=s.status;document.getElementById('tripState').textContent=`${s.fixture||'-'} · accepted ${s.raw_debug?.accepted_count??0} · rejected ${s.raw_debug?.rejected_count??0}`;document.getElementById('replay').textContent=JSON.stringify(s.replay,null,2);document.getElementById('events').innerHTML=(s.events||[]).map(e=>`<tr><td>${e.sequence??''}</td><td>${e.timestamp??''}</td><td>${e.latitude??''}</td><td>${e.longitude??''}</td><td>${e.horizontal_accuracy_m??''}</td><td>${e.accepted}</td></tr>`).join('');drawMap(s.events);document.getElementById('windows').textContent=JSON.stringify(s.window_predictions||'WAITING',null,2);document.getElementById('transit').textContent=JSON.stringify(p.transit_context||'WAITING',null,2);document.getElementById('expected').textContent=JSON.stringify(p.expected_behaviour||'WAITING',null,2);document.getElementById('pipeline').textContent=JSON.stringify(p,null,2);document.getElementById('raw').textContent=JSON.stringify(s.raw_debug,null,2);document.getElementById('actualMode').textContent=p.actual_behaviour?.final_mode||'-';document.getElementById('expectedMode').textContent=p.expected_behaviour?.predicted_mode||'-';document.getElementById('actualCo2').textContent=p.co2?`${Number(p.co2.actual_co2e_g).toFixed(1)} g`:'-';document.getElementById('expectedCo2').textContent=p.co2?`${Number(p.co2.expected_co2e_g).toFixed(1)} g`:'-';document.getElementById('reduction').textContent=p.co2?`${Number(p.co2.reduction_co2e_g).toFixed(1)} g`:'-';document.getElementById('homeReduction').textContent=p.co2?`${Number(p.co2.reduction_co2e_g).toFixed(1)} g`:'0 g';document.getElementById('homeDistance').textContent=p.distance_km?`${Number(p.distance_km).toFixed(2)} km`:'0 km'}
async function init(){const f=await json('/api/fixtures');document.getElementById('fixture').innerHTML=f.map(x=>`<option value="${x}">${x}</option>`).join('');toggleDeveloper();refresh();setInterval(refresh,1000)}init();
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
        self.window_predictions: list[dict[str, Any]] = []
        self.view_mode = "user"

    def start(self, fixture: str, speed: str, expected_features: dict[str, object] | None = None, view_mode: str = "user") -> None:
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
            self.view_mode = view_mode if view_mode in {"user", "developer"} else "user"
            self.expected_features = (
                expected_features
                if self.view_mode == "developer"
                else (_default_expected_features() if path == DEFAULT_MOCK else None)
            )
            self.window_predictions = []
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
            try:
                self.window_predictions = [
                    {
                        "window_start": window.window_start.isoformat(),
                        "window_end": window.window_end.isoformat(),
                        "status": window.status,
                        "predicted_mode": window.predicted_mode,
                        "confidence": window.confidence,
                        "probabilities": window.probabilities,
                        "features": window.features,
                    }
                    for window in infer_windows(
                        session.events,
                        model_path=ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib",
                        window_seconds=120,
                    )
                ]
            except Exception as error:
                self.window_predictions = [{"status": "FAIL", "reason": str(error)}]
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
            return {"status": self.status, "view_mode": self.view_mode, "fixture": self.fixture, "replay": dict(self.replay), "pipeline": self.pipeline, "window_predictions": list(self.window_predictions), "events": list(self.events), "raw_debug": {"event_count": len(self.events), "accepted_count": sum(bool(event["accepted"]) for event in self.events), "rejected_count": sum(not bool(event["accepted"]) for event in self.events)}}


class _WaitingForInput(ValueError):
    """Pipeline cannot run until the user supplies required KTDB conditions."""


RUNTIME = Runtime()
FIXTURE_DIR = ROOT / "data/fixtures/integration"


def _fixture_path(name: str) -> Path:
    if name.startswith("mock/"):
        candidate = (MOCK_DIR / name.removeprefix("mock/")).resolve()
        root = MOCK_DIR.resolve()
    else:
        candidate = (FIXTURE_DIR / name).resolve()
        root = FIXTURE_DIR.resolve()
    if candidate.parent != root or candidate.suffix.lower() != ".csv" or not candidate.is_file():
        raise ValueError("fixture must be an existing CSV under data/fixtures/integration or mock")
    return candidate


def _default_expected_features() -> dict[str, object] | None:
    if not DEFAULT_KTDB_SAMPLE.is_file():
        return None
    sample = pd.read_csv(DEFAULT_KTDB_SAMPLE, nrows=1, encoding="utf-8-sig").iloc[0]
    return {name: sample[name] for name in MODEL_FEATURES}


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
            self._send(200, IPHONE_HTML, "text/html")
        elif path == "/api/fixtures":
            fixture_names = sorted(path.name for path in FIXTURE_DIR.glob("*.csv"))
            if DEFAULT_MOCK.is_file():
                fixture_names.insert(0, "mock/" + DEFAULT_MOCK.name)
            self._send(200, fixture_names)
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
                RUNTIME.start(str(body["fixture"]), str(body.get("speed", "instant")), expected, str(body.get("view_mode", "user")))
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
