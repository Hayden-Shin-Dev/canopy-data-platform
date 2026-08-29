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
from src.integration.distance import trajectory_distance_km
from src.integration.gps_contract import validate_gps_event
from src.integration.ktdb_context import build_expected_features
from src.predict_expected_behaviour import predict_expected_behaviour
from src.integration.emissions import calculate_expected_emission, load_factor_resolver
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
<section><h2>오늘의 이동</h2><div class="metric"><span>탄소 절감</span><strong id="homeReduction">0 g</strong></div><div class="metric"><span>이동 거리</span><strong id="homeDistance">0 km</strong></div><button class="primary" onclick="start()">이동 시작</button><button onclick="setMode('developer')">Developer Mode</button></section>
<section class="developer-only" id="testControls"><h2>Test Mode</h2><label>입력 <select id="fixture"></select></label><label>Replay <select id="speed"><option>instant</option><option>1</option><option>5</option><option>10</option><option>30</option></select></label><label>화면 <select id="viewMode" onchange="toggleDeveloper()"><option value="user">User Mode</option><option value="developer">Developer Mode</option></select></label><div><button onclick="start()">Start</button><button onclick="post('/api/pause')">Pause</button><button onclick="post('/api/resume')">Resume</button><button onclick="post('/api/stop')">Stop</button></div><p id="status">WAITING</p></section>
<section><h2>Baseline Preview</h2><p>현재 조건에서 예상되는 이동행동</p><div id="baselineBars" class="muted">결과 계산 후 표시됩니다.</div></section>
<section><h2>Active Trip</h2><p id="tripState">이동을 시작하면 현재 GPS를 표시합니다.</p><svg viewBox="0 0 100 100"><polyline id="path" fill="none" stroke="#1d7a55" stroke-width="1.5" points=""/></svg><pre id="replay" class="developer-only">-</pre><table class="developer-only"><thead><tr><th>sequence</th><th>timestamp</th><th>latitude</th><th>longitude</th><th>accuracy</th><th>accepted</th></tr></thead><tbody id="events"></tbody></table></section>
<section><h2>Trip Result</h2><div class="metric"><span>실제 감지 이동수단</span><strong id="actualMode">-</strong></div><div class="metric"><span>예상 이동수단</span><strong id="expectedMode">-</strong></div><div class="metric"><span>실제 배출량</span><span id="actualCo2">-</span></div><div class="metric"><span>예상 배출량</span><span id="expectedCo2">-</span></div><div class="metric"><span>절감량</span><span id="reduction">-</span></div></section>
<section><h2>Trip Detail</h2><p id="tripDetail">이동 종료 후 backend 결과를 표시합니다.</p></section>
<section class="developer-only" id="developer"><h2>Developer Mode</h2><h3>120s GeoLife Windows</h3><pre id="windows">WAITING</pre><h3>Transit Context</h3><pre id="transit">WAITING</pre><h3>KTDB Expected Behaviour</h3><p>기존 KTDB feature JSON은 Developer Mode에서만 입력합니다.</p><textarea id="expectedInput" rows="5" style="width:100%" placeholder='{"weekday": "weekday", "departure_hour": 8, ...}'></textarea><pre id="expected">WAITING</pre><h3>Full Pipeline / Raw Debug</h3><pre id="pipeline">WAITING</pre><pre id="raw">-</pre></section>
<script>
async function json(url,options){const r=await fetch(url,options);return await r.json()} async function post(url){await json(url,{method:'POST'})} function toggleDeveloper(){const dev=document.getElementById('viewMode').value==='developer';document.getElementById('developer').style.display=dev?'block':'none';document.getElementById('testControls').style.display=dev?'block':'none'} function setMode(mode){document.getElementById('viewMode').value=mode;toggleDeveloper()}
async function start(){let expected_features=null;if(document.getElementById('viewMode').value==='developer'){const text=document.getElementById('expectedInput').value.trim();if(text)expected_features=JSON.parse(text)}await json('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fixture:document.getElementById('fixture').value,speed:document.getElementById('speed').value,expected_features,view_mode:document.getElementById('viewMode').value})})}
function drawMap(events){const v=(events||[]).filter(e=>e.accepted&&e.latitude!==undefined);if(!v.length)return;const a=v.map(e=>+e.latitude),o=v.map(e=>+e.longitude),la=Math.min(...a),ha=Math.max(...a),lo=Math.min(...o),ho=Math.max(...o),dy=ha-la||1e-6,dx=ho-lo||1e-6;document.getElementById('path').setAttribute('points',v.map(e=>`${((+e.longitude-lo)/dx*90+5).toFixed(2)},${(95-(+e.latitude-la)/dy*90).toFixed(2)}`).join(' '))}
async function refresh(){const s=await json('/api/status'),p=s.pipeline||{};document.getElementById('status').textContent=s.status;document.getElementById('tripState').textContent=`${s.fixture||'-'} · accepted ${s.raw_debug?.accepted_count??0} · rejected ${s.raw_debug?.rejected_count??0}`;document.getElementById('replay').textContent=JSON.stringify(s.replay,null,2);document.getElementById('events').innerHTML=(s.events||[]).map(e=>`<tr><td>${e.sequence??''}</td><td>${e.timestamp??''}</td><td>${e.latitude??''}</td><td>${e.longitude??''}</td><td>${e.horizontal_accuracy_m??''}</td><td>${e.accepted}</td></tr>`).join('');drawMap(s.events);document.getElementById('windows').textContent=JSON.stringify(s.window_predictions||'WAITING',null,2);document.getElementById('transit').textContent=JSON.stringify(p.transit_context||'WAITING',null,2);document.getElementById('expected').textContent=JSON.stringify(p.expected_behaviour||'WAITING',null,2);document.getElementById('pipeline').textContent=JSON.stringify(p,null,2);document.getElementById('raw').textContent=JSON.stringify(s.raw_debug,null,2);document.getElementById('actualMode').textContent=p.actual_behaviour?.final_mode||'-';document.getElementById('expectedMode').textContent=p.expected_behaviour?.predicted_mode||'-';document.getElementById('actualCo2').textContent=p.co2?`${Number(p.co2.actual_co2e_g).toFixed(1)} g`:'-';document.getElementById('expectedCo2').textContent=p.co2?`${Number(p.co2.expected_co2e_g).toFixed(1)} g`:'-';document.getElementById('reduction').textContent=p.co2?`${Number(p.co2.reduction_co2e_g).toFixed(1)} g`:'-';document.getElementById('homeReduction').textContent=p.co2?`${Number(p.co2.reduction_co2e_g).toFixed(1)} g`:'0 g';document.getElementById('homeDistance').textContent=p.distance_km?`${Number(p.distance_km).toFixed(2)} km`:'0 km'}
async function updateDerived(){const s=await json('/api/status'),p=s.pipeline||{};const probs=p.expected_behaviour?.probabilities||{};document.getElementById('baselineBars').innerHTML=Object.entries(probs).map(([m,v])=>`<div class="metric"><span>${m}</span><span>${(Number(v)*100).toFixed(1)}%</span></div>`).join('')||'결과 계산 후 표시됩니다.';if(p.distance_km)document.getElementById('tripDetail').textContent=`${s.fixture||'-'} · ${Number(p.distance_km).toFixed(2)} km · ${p.accepted_event_count||0} GPS events`;}
async function init(){const f=await json('/api/fixtures');document.getElementById('fixture').innerHTML=f.map(x=>`<option value="${x}">${x}</option>`).join('');setMode('user');refresh();setInterval(refresh,1000);setInterval(updateDerived,1000)}init();
</script></body></html>"""


MOBILE_APP_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Canopy</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""><style>
*{box-sizing:border-box}body{margin:0;background:#dfe5e2;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#14231d}#phone{width:400px;max-width:100vw;height:820px;max-height:100vh;margin:0 auto;background:#f8faf9;position:relative;overflow:hidden;box-shadow:0 18px 60px #17352a33}header{height:68px;padding:22px 20px 10px;display:flex;justify-content:space-between;align-items:center;position:absolute;z-index:20;inset:0 0 auto;background:linear-gradient(#fff,transparent);pointer-events:none}header>*{pointer-events:auto}header strong{font-size:18px;letter-spacing:.12em}header button{border:0;background:#ffffffdd;border-radius:20px;padding:8px 11px;font-size:12px}.screen{position:absolute;inset:0;display:none;animation:slideIn .28s ease-out}.screen.active{display:block}@keyframes slideIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}.map{position:absolute;inset:0 0 160px;z-index:1}.leaflet-container{font:inherit}.leaflet-control-attribution{font-size:8px}.sheet{position:absolute;z-index:5;left:10px;right:10px;bottom:10px;background:#fffffff2;border-radius:24px;padding:18px 18px 16px;box-shadow:0 8px 30px #17352a30;backdrop-filter:blur(14px);animation:sheetUp .35s ease-out}@keyframes sheetUp{from{transform:translateY(20px);opacity:0}to{transform:none;opacity:1}}.eyebrow{font-size:11px;color:#618074;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.route{display:grid;gap:8px;margin:10px 0 14px}.route div{display:flex;gap:9px;align-items:flex-start;font-size:13px}.dot{width:9px;height:9px;border-radius:50%;background:#2e9c70;margin-top:4px}.dot.end{background:#e07055}.muted{font-size:11px;color:#6a7771;margin-top:2px}.baseline{border-top:1px solid #e6ece8;padding-top:12px;margin-top:8px}.baseline h3{font-size:15px;margin:4px 0}.bar{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:11px}.bar span:first-child{width:38px}.bar i{height:7px;background:#54a982;border-radius:8px;display:block;min-width:2px;transition:width .5s}.bar b{font-weight:600}.cta{width:100%;border:0;border-radius:14px;padding:14px;background:#177950;color:#fff;font-size:15px;font-weight:700;margin-top:12px;box-shadow:0 5px 12px #17795044}.cta:active,button:active{transform:scale(.97)}.status{font-size:20px;font-weight:700;margin:5px 0 12px}.status-sub{font-size:12px;color:#65746d}.stats{display:flex;gap:8px;margin-top:14px}.stat{flex:1;background:#f0f5f2;border-radius:12px;padding:9px}.stat small{display:block;color:#718078;font-size:10px}.stat strong{display:block;margin-top:3px;font-size:15px}.stop{background:#fff;border:1px solid #e0e7e2;color:#b34d3c}.result-title{font-size:22px;font-weight:750;margin:4px 0 12px}.compare{display:grid;gap:8px;margin:12px 0}.compare-row{display:flex;justify-content:space-between;align-items:center;background:#f3f6f4;border-radius:11px;padding:10px 12px;font-size:12px}.compare-row strong{font-size:16px}.reduction{background:#e2f4ea;color:#147146;border-radius:13px;padding:13px;text-align:center;margin-top:10px}.reduction strong{font-size:24px;display:block}.developer{background:#f8faf9;overflow:auto;padding:80px 14px 18px}.developer h2{margin:0 0 12px}.developer label{display:block;font-size:12px;margin:8px 0}.developer select,.developer textarea{width:100%;padding:8px;border:1px solid #ccd8d1;border-radius:8px;background:#fff}.developer button{padding:8px 10px;border:1px solid #cbd8d0;border-radius:8px;background:#fff;margin:3px 0}.developer pre{white-space:pre-wrap;overflow:auto;background:#edf2ef;border-radius:8px;padding:8px;font-size:10px}.developer table{font-size:9px;width:100%;display:block;overflow:auto;max-height:180px}.developer td,.developer th{padding:3px;border:1px solid #dbe4df;white-space:nowrap}
</style></head><body><div id="phone"><header><strong>CANOPY</strong><button onclick="openDeveloper()">Developer</button></header>
<section id="home" class="screen active"><div id="homeMap" class="map"></div><div class="sheet"><div class="eyebrow">오늘의 출근</div><div class="route"><div><span class="dot"></span><div><b>서울 영등포구 버드나루로10길 7</b><div class="muted">출발지</div></div></div><div><span class="dot end"></span><div><b>Microsoft Korea</b><div class="muted">서울 종로구 종로1길 50</div></div></div></div><div class="baseline"><div class="eyebrow">Population baseline</div><h3>비슷한 조건의 사람들은 보통 어떻게 이동했을까요?</h3><div id="baselineBars">불러오는 중...</div></div><button class="cta" onclick="startTrip()">출근 시작하기</button></div></section>
<section id="active" class="screen"><div id="activeMap" class="map"></div><div class="sheet"><div class="eyebrow">ACTIVE TRIP</div><div id="activeStatus" class="status">이동 패턴을 확인하고 있어요</div><div id="activeSub" class="status-sub">120초 Window가 준비되면 실제 모델 결과를 보여드려요.</div><div class="stats"><div class="stat"><small>현재 이동수단</small><strong id="activeMode">확인 중</strong></div><div class="stat"><small>이동 시간</small><strong id="activeTime">00:00</strong></div><div class="stat"><small>현재 거리</small><strong id="activeDistance">0.00 km</strong></div></div><button class="cta stop" onclick="finishTrip()">이동 종료</button></div></section>
<section id="result" class="screen"><div id="resultMap" class="map"></div><div class="sheet"><div class="eyebrow">TRIP COMPLETE</div><div class="result-title">오늘의 이동이 끝났어요</div><div class="stats"><div class="stat"><small>총 이동거리</small><strong id="resultDistance">-</strong></div><div class="stat"><small>총 이동시간</small><strong id="resultTime">-</strong></div></div><div class="compare"><div class="compare-row"><span>비슷한 조건의 이동 · Expected CO2</span><strong id="resultExpected">-</strong></div><div class="compare-row"><span>나의 실제 이동 · Actual CO2</span><strong id="resultActual">-</strong></div></div><div class="reduction"><span>CO2 Reduction</span><strong id="resultReduction">-</strong></div><p class="muted">감지된 이동수단: <b id="resultMode">-</b></p><button class="cta" onclick="showScreen('home')">홈으로</button></div></section>
<section id="developer" class="screen developer"><h2>Developer Mode</h2><label>Fixture<select id="fixture"></select></label><label>Replay speed<select id="speed"><option>instant</option><option>1</option><option>5</option><option>10</option><option>30</option></select></label><textarea id="expectedInput" rows="4" placeholder="기존 KTDB MODEL_FEATURES JSON (선택)"></textarea><button onclick="startDeveloper()">Replay 실행</button><button onclick="showScreen('home')">User Mode로 돌아가기</button><h3>Replay / raw GPS</h3><pre id="replay">-</pre><h3>120s Window / GeoLife</h3><pre id="windows">WAITING</pre><h3>Transit / KTDB / Emission</h3><pre id="pipeline">WAITING</pre></section>
</div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script><script>
const maps={},layers={},route={};let pollTimer=null,currentScreen='home';
async function api(url,options){const r=await fetch(url,options);return await r.json()}
function showScreen(name){currentScreen=name;document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));document.getElementById(name).classList.add('active');Object.values(maps).forEach(m=>setTimeout(()=>m.invalidateSize(),30))}
function openDeveloper(){showScreen('developer')}
function setupMap(id){if(!window.L)return null;const map=L.map(id,{zoomControl:false}).setView([37.55,126.95],12);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);maps[id]=map;layers[id]={route:L.layerGroup().addTo(map),path:L.polyline([],{color:'#19835b',weight:5,opacity:.9}).addTo(map)};return map}
function drawMaps(events=[]){const points=events.filter(e=>e.accepted&&e.latitude!==undefined).map(e=>[+e.latitude,+e.longitude]);const all=[route.origin&&[route.origin.latitude,route.origin.longitude],route.destination&&[route.destination.latitude,route.destination.longitude]].filter(Boolean);Object.entries(maps).forEach(([id,map])=>{const group=layers[id].route;group.clearLayers();if(route.origin)L.circleMarker([route.origin.latitude,route.origin.longitude],{radius:7,color:'#238e65',fillColor:'#fff',fillOpacity:1}).bindTooltip('출발').addTo(group);if(route.destination)L.circleMarker([route.destination.latitude,route.destination.longitude],{radius:7,color:'#dc7058',fillColor:'#fff',fillOpacity:1}).bindTooltip('도착').addTo(group);layers[id].path.setLatLngs(id==='homeMap'?all:points);if(points.length){if(!layers[id].current)layers[id].current=L.circleMarker(points[points.length-1],{radius:8,color:'#135f43',fillColor:'#45bd88',fillOpacity:1}).addTo(map);else layers[id].current.setLatLng(points[points.length-1]);}const fit=(id==='homeMap'?all:points.length?points:all);if(fit.length)map.fitBounds(fit,{padding:[35,35],maxZoom:15})})}
function renderBaseline(data){const el=document.getElementById('baselineBars');if(!data||data.status!=='READY'){el.textContent='Baseline을 불러오지 못했습니다.';return}const names={car:'자동차',bus:'버스',rail:'철도',walk:'도보',bike:'자전거'};el.innerHTML=Object.entries(data.probabilities).map(([mode,value])=>`<div class="bar"><span>${names[mode]||mode}</span><i style="width:${Math.max(2,Number(value)*100)}%"></i><b>${(Number(value)*100).toFixed(1)}%</b></div>`).join('')}
function formatTime(seconds){const s=Math.max(0,Math.floor(seconds||0));return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`}
function modeText(mode,transit){if(transit&&transit.matched_subway_line)return `${transit.matched_subway_line}호선을 타셨네요!`;return {walk:'지금은 걷는 중!',bike:'자전거로 이동 중이에요',car:'자동차로 이동 중이에요',bus:'버스를 타셨네요!',rail:'지하철/철도로 이동 중이에요'}[mode]||'이동 패턴을 확인하고 있어요'}
function updateFromStatus(s){const events=s.events||[];drawMaps(events);const p=s.pipeline||{};document.getElementById('activeDistance').textContent=`${Number(s.live_distance_km||0).toFixed(2)} km`;if(events.length){const first=new Date(events[0].timestamp),last=new Date(events[events.length-1].timestamp);document.getElementById('activeTime').textContent=formatTime((last-first)/1000)}const windows=s.window_predictions||[];const latest=[...windows].reverse().find(w=>w.status==='READY');if(latest){document.getElementById('activeMode').textContent=modeText(latest.predicted_mode,p.transit_context);document.getElementById('activeStatus').textContent=modeText(latest.predicted_mode,p.transit_context);document.getElementById('activeSub').textContent=`${latest.window_start} · confidence ${(Number(latest.confidence||0)*100).toFixed(0)}%`}if(p.status==='PASS'){document.getElementById('resultDistance').textContent=`${Number(p.distance_km||0).toFixed(2)} km`;document.getElementById('resultExpected').textContent=`${Number(p.co2?.expected_co2e_g||0).toFixed(1)} g`;document.getElementById('resultActual').textContent=`${Number(p.co2?.actual_co2e_g||0).toFixed(1)} g`;document.getElementById('resultReduction').textContent=`${Number(p.co2?.reduction_co2e_g||0).toFixed(1)} g`;document.getElementById('resultMode').textContent=p.actual_behaviour?.final_mode||'-';document.getElementById('resultTime').textContent=events.length?formatTime((new Date(events[events.length-1].timestamp)-new Date(events[0].timestamp))/1000):'-';if(currentScreen==='active')showScreen('result')}}
async function refresh(){const s=await api('/api/status');updateFromStatus(s);document.getElementById('replay').textContent=JSON.stringify(s.replay,null,2);document.getElementById('windows').textContent=JSON.stringify(s.window_predictions||'WAITING',null,2);document.getElementById('pipeline').textContent=JSON.stringify(s.pipeline||'WAITING',null,2)}
async function startTrip(){showScreen('active');await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fixture:'mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv',speed:'30',view_mode:'user'})});}
async function finishTrip(){await api('/api/stop',{method:'POST'});}
async function startDeveloper(){let expected=null;const text=document.getElementById('expectedInput').value.trim();if(text)expected=JSON.parse(text);showScreen('active');await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fixture:document.getElementById('fixture').value,speed:document.getElementById('speed').value,expected_features:expected,view_mode:'developer'})});}
async function init(){let r={};try{r=await api('/api/route')}catch(e){console.warn('route loading failed',e)}Object.assign(route,r);let b={status:'WAITING'};try{b=await api('/api/baseline')}catch(e){console.warn('baseline loading failed',e)}renderBaseline(b);let f=[];try{f=await api('/api/fixtures')}catch(e){console.warn('fixture loading failed',e)}document.getElementById('fixture').innerHTML=f.map(x=>`<option value="${x}">${x}</option>`).join('');setupMap('homeMap');setupMap('activeMap');setupMap('resultMap');drawMaps();refresh().catch(e=>console.warn('status loading failed',e));pollTimer=setInterval(()=>refresh().catch(e=>console.warn('status refresh failed',e)),700)}init();
</script></body></html>"""


# Result 화면은 backend segment 배열을 그대로 노출한다.
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "</style></head>",
    "</style><style>.segments{display:grid;gap:6px;margin:12px 0}.segment{display:flex;justify-content:space-between;align-items:center;background:#f0f5f2;border-radius:10px;padding:8px 10px;font-size:11px}.segment strong{display:block;font-size:13px}.segment small{color:#718078}</style></head>",
).replace(
    '<div class="compare"><div class="compare-row"><span>비슷한 조건의 이동 · Expected CO2</span>',
    '<div class="segments" id="resultSegments"></div><div class="compare"><div class="compare-row"><span>비슷한 조건의 이동 · Expected CO2</span>',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function updateFromStatus(s){",
    "function renderSegments(segments){const el=document.getElementById('resultSegments');if(!el)return;const names={walk:'도보',bike:'자전거',car:'자동차',bus:'버스',rail:'철도'};el.innerHTML=(segments||[]).map(x=>'<div class=segment><strong>'+(x.mode==='rail'&&x.matched_subway_line?x.matched_subway_line+'호선':names[x.mode]||x.mode)+'</strong><span><b>'+Number(x.distance_km||0).toFixed(2)+' km</b><small> · '+Number(x.co2e_g||0).toFixed(1)+' g</small></span></div>').join('')}\nfunction updateFromStatus(s){",
).replace(
    "document.getElementById('resultMode').textContent=p.actual_behaviour?.final_mode||'-';",
    "document.getElementById('resultMode').textContent=(p.actual_behaviour?.mode_sequence||[]).filter((x,i,a)=>i===0||x!==a[i-1]).join(' → ')||p.actual_behaviour?.final_mode||'-';renderSegments(p.actual_behaviour?.segments||[]);",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "if(latest){document.getElementById('activeMode').textContent=modeText(latest.predicted_mode,p.transit_context);document.getElementById('activeStatus').textContent=modeText(latest.predicted_mode,p.transit_context);",
    "if(latest){const resolvedLatest=[...(p.window_results||[])].reverse().find(w=>w.window_start===latest.window_start);const activeMode=resolvedLatest?.final_mode||latest.predicted_mode;const activeTransit=resolvedLatest?.transit_context||p.transit_context;document.getElementById('activeMode').textContent=modeText(activeMode,activeTransit);document.getElementById('activeStatus').textContent=modeText(activeMode,activeTransit);",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function modeText(mode,transit){if(transit&&transit.matched_subway_line)return",
    "function modeText(mode,transit){if(mode==='rail'&&transit&&transit.matched_subway_line)return",
)

# 이동수단 전환은 실제 추론 결과를 그대로 받아 간단한 SVG로 표현한다.
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "</style></head>",
    "</style><style>.mode-visual{height:34px;display:flex;align-items:center;justify-content:center;margin:-4px 0 2px;overflow:hidden;color:#177950;transition:color .2s ease}.mode-visual[data-mode=\\\"bike\\\"]{color:#2875b8}.mode-visual[data-mode=\\\"car\\\"]{color:#7452a8}.mode-visual[data-mode=\\\"bus\\\"]{color:#b06435}.mode-visual[data-mode=\\\"rail\\\"]{color:#c04f5a}.mode-visual svg{width:96px;height:30px}.mode-visual .mode-track{stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-dasharray:5 5;animation:trackMove .8s linear infinite}.mode-visual .mode-body{fill:currentColor;opacity:.9}.mode-visual .mode-wheel{fill:#fff;stroke:currentColor;stroke-width:2}.mode-visual .mode-window{fill:#fff;opacity:.85}.mode-visual .mode-walk{fill:currentColor;animation:walkBob .7s ease-in-out infinite}.mode-visual .mode-bike{animation:bikeRoll 1s linear infinite;transform-origin:50% 22px}.mode-visual .mode-car{animation:carDrive 1.4s ease-in-out infinite}.mode-visual .mode-bus{animation:busDrive 1.2s ease-in-out infinite}.mode-visual .mode-rail{animation:railSlide 1.6s ease-in-out infinite}@keyframes walkBob{0%,100%{transform:translateY(1px)}50%{transform:translateY(-2px)}}@keyframes bikeRoll{to{transform:rotate(360deg)}}@keyframes carDrive{0%,100%{transform:translateX(-3px)}50%{transform:translateX(3px)}}@keyframes busDrive{0%,100%{transform:translateX(3px)}50%{transform:translateX(-3px)}}@keyframes railSlide{0%,100%{transform:translateX(-4px)}50%{transform:translateX(4px)}}@keyframes trackMove{to{stroke-dashoffset:-10}}</style></head>",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<div id="activeStatus" class="status">',
    '<div id="activeStatus" class="status"><div id="modeVisual" class="mode-visual" data-mode="unknown" aria-hidden="true"></div>',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function modeText(mode,transit){",
    "function renderModeVisual(mode){const el=document.getElementById('modeVisual');if(!el)return;const safe=['walk','bike','car','bus','rail'].includes(mode)?mode:'unknown';const visuals={walk:`<svg viewBox='0 0 100 38' role='img' aria-label='walk mode'><path class='mode-track' d='M5 34h90'/><circle class='mode-walk' cx='50' cy='12' r='4'/><path class='mode-walk' d='M47 17h6l4 11h-4l-3-6-4 6h-4z'/></svg>`,bike:`<svg viewBox='0 0 100 38' role='img' aria-label='bike mode'><path class='mode-track' d='M5 34h90'/><g class='mode-bike'><circle class='mode-wheel' cx='36' cy='24' r='8'/><circle class='mode-wheel' cx='64' cy='24' r='8'/><path d='M36 24l10-11 9 11m-9-11h9l9 11m-18-5h10' fill='none' stroke='currentColor' stroke-width='2'/></g></svg>`,car:`<svg viewBox='0 0 100 38' role='img' aria-label='car mode'><path class='mode-track' d='M5 34h90'/><g class='mode-car'><path class='mode-body' d='M28 25l6-10h25l10 10v6H28z'/><path class='mode-window' d='M38 16h8v7h-12zm11 0h9l6 7H49z'/><circle class='mode-wheel' cx='38' cy='30' r='4'/><circle class='mode-wheel' cx='62' cy='30' r='4'/></g></svg>`,bus:`<svg viewBox='0 0 100 38' role='img' aria-label='bus mode'><path class='mode-track' d='M5 34h90'/><g class='mode-bus'><rect class='mode-body' x='27' y='10' width='46' height='21' rx='4'/><path class='mode-window' d='M31 14h9v7h-9zm12 0h9v7h-9zm12 0h9v7h-9z'/><circle class='mode-wheel' cx='37' cy='31' r='4'/><circle class='mode-wheel' cx='63' cy='31' r='4'/></g></svg>`,rail:`<svg viewBox='0 0 100 38' role='img' aria-label='rail mode'><path class='mode-track' d='M5 34h90'/><g class='mode-rail'><rect class='mode-body' x='25' y='9' width='50' height='21' rx='6'/><path class='mode-window' d='M30 13h12v8H30zm16 0h12v8H46zm16 0h8v8h-8z'/><circle class='mode-wheel' cx='36' cy='31' r='3'/><circle class='mode-wheel' cx='64' cy='31' r='3'/></g></svg>`};el.dataset.mode=safe;el.innerHTML=visuals[safe]||visuals.walk}function modeText(mode,transit){",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "document.getElementById('activeStatus').textContent=modeText(activeMode,activeTransit);",
    "renderModeVisual(activeMode);document.getElementById('activeStatus').textContent=modeText(activeMode,activeTransit);",
)

# Result 이후에는 실제 감축량을 Token으로 환산해 보상 화면까지 이어간다.
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "</style></head>",
    "</style><style>.reward-card{text-align:center;padding:28px 18px}.token-burst{font-size:54px;animation:tokenPop .7s ease-out}.token-earned{font-size:30px;color:#177950;margin:8px 0}.token-balance{font-size:13px;color:#63756c}.reward-note{font-size:12px;color:#718078;margin:8px 0 18px}.text-button{border:0;background:none;color:#5c7469;font-size:13px;margin-top:10px;padding:8px 16px}.home-distance{display:flex;justify-content:space-between;align-items:center;background:#f0f5f2;border-radius:12px;padding:10px 12px;margin:10px 0;font-size:12px}.profile-screen{overflow:auto;padding:82px 16px 92px}.profile-screen h2{font-size:24px;margin:0 0 6px}.profile-screen .profile-card{background:#fff;border-radius:18px;padding:18px;margin-top:14px;box-shadow:0 5px 18px #17352a12}.profile-screen .profile-token{font-size:34px;color:#177950;font-weight:750}.profile-screen .history-row{display:flex;justify-content:space-between;padding:11px 0;border-bottom:1px solid #edf1ee;font-size:12px}.profile-screen .history-row:last-child{border-bottom:0}.bottom-nav{position:absolute;z-index:30;left:10px;right:10px;bottom:10px;height:58px;display:flex;align-items:stretch;justify-content:space-around;background:#fffffff2;border:1px solid #e2e9e4;border-radius:18px;box-shadow:0 8px 24px #17352a24;backdrop-filter:blur(14px)}.bottom-nav button{flex:1;border:0;background:none;color:#77857e;font-size:11px;font-weight:600}.bottom-nav button.active{color:#177950}.bottom-nav button span{display:block;font-size:18px;line-height:20px;margin-bottom:2px}@keyframes tokenPop{0%{transform:scale(.5);opacity:0}70%{transform:scale(1.12)}100%{transform:scale(1);opacity:1}}</style></head>",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<section id="developer" class="screen developer">',
    '<section id="reward" class="screen"><div class="sheet reward-card"><div class="eyebrow">CANOPY TOKEN</div><div class="token-burst" aria-hidden="true">✦</div><div class="token-earned" id="tokenEarned">+0 Token</div><div class="reward-note" id="rewardNote">이번 이동의 CO2 감축량을 기준으로 계산했습니다.</div><div class="token-balance">현재 보유 <strong id="tokenBalance">0</strong> Token</div><button class="cta" onclick="showScreen(\'result\')">결과 확인</button><button class="text-button" onclick="showScreen(\'home\')">홈으로</button></div></section><section id="developer" class="screen developer">',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<div class="baseline"><div class="eyebrow">Population baseline</div>',
    '<div class="home-distance"><span>집에서 직장까지</span><strong id="homeRouteDistance">거리 계산 중</strong></div><div class="baseline"><div class="eyebrow">Population baseline</div>',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<section id="active" class="screen">',
    '<section id="journey" class="screen"><div id="journeyMap" class="map"></div><div class="sheet"><div class="eyebrow">여정</div><div class="status">오늘의 출근 여정</div><div class="route"><div><span class="dot"></span><div><b>서울 영등포구 버드나루로10길 7</b><div class="muted">집</div></div></div><div><span class="dot end"></span><div><b>Microsoft Korea</b><div class="muted">직장</div></div></div></div><div class="home-distance"><span>예상 이동 거리</span><strong id="journeyDistance">-</strong></div><button class="cta" onclick="startTrip()">출근 시작하기</button></div></section><section id="active" class="screen">',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<div class="eyebrow">?ㅻ뒛??異쒓렐</div>',
    '<div class="eyebrow">?ㅻ뒛??異쒓렐</div><div class="token-balance">Canopy Token <strong id="homeTokenBalance">0</strong></div>',
)
# 템플릿 인코딩이 달라도 홈 화면에 Token 잔액이 반드시 존재하도록 보강한다.
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '<section id="home" class="screen active"><div id="homeMap" class="map"></div><div class="sheet"><div class="eyebrow">오늘의 출근</div>',
    '<section id="home" class="screen active"><div id="homeMap" class="map"></div><div class="sheet"><div class="eyebrow">오늘의 출근</div><div class="token-balance">Canopy Token <strong id="homeTokenBalance">0</strong></div>',
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "const maps={},layers={},route={};let pollTimer=null,currentScreen='home';",
    "const maps={},layers={},route={};let pollTimer=null,currentScreen='home';let rewardShown=false;const TOKEN_GRAMS_PER_TOKEN=10;let tokenBalance=Number(localStorage.getItem('canopyTokenBalance')||0);",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function showScreen(name){currentScreen=name;",
    "function showScreen(name){currentScreen=name;const homeToken=document.getElementById('homeTokenBalance');const rewardToken=document.getElementById('tokenBalance');if(homeToken)homeToken.textContent=tokenBalance;if(rewardToken)rewardToken.textContent=tokenBalance;const myToken=document.getElementById('myTokenBalance');if(myToken)myToken.textContent=tokenBalance+' Token';if(name==='mypage')renderMyPage();document.querySelectorAll('.bottom-nav button').forEach(button=>button.classList.toggle('active',button.dataset.tab===(name==='active'||name==='result'||name==='reward'?'journey':name)));document.querySelectorAll('.bottom-nav').forEach(nav=>nav.style.display=name==='developer'?'none':'flex');",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function openDeveloper(){showScreen('developer')}",
    "function renderMyPage(){const balance=document.getElementById('myTokenBalance');if(balance)balance.textContent=tokenBalance+' Token';const target=document.getElementById('myRewardHistory');if(!target)return;let history=[];try{history=JSON.parse(localStorage.getItem('canopyTokenHistory')||'[]')}catch(e){history=[]}target.innerHTML=history.length?history.map(item=>'<div class=history-row><span>'+item.date+'</span><strong>+'+item.earned+' Token</strong></div>').join(''):'<p class=muted>아직 받은 Token이 없어요.</p>'}function navigateTab(tab){if(tab==='home')return showScreen('home');if(tab==='mypage')return showScreen('mypage');if(currentScreen==='active'||currentScreen==='result'||currentScreen==='reward')return showScreen(currentScreen==='reward'?'result':currentScreen);showScreen('journey')}function openDeveloper(){showScreen('developer')}",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function drawMaps(events=[]){",
    "function updateRouteDistance(){if(!route.origin||!route.destination)return;const rad=Math.PI/180,a=route.origin.latitude*rad,b=route.destination.latitude*rad,c=(route.destination.latitude-route.origin.latitude)*rad,d=(route.destination.longitude-route.origin.longitude)*rad;const km=6371*2*Math.asin(Math.sqrt(Math.sin(c/2)**2+Math.cos(a)*Math.cos(b)*Math.sin(d/2)**2));['homeRouteDistance','journeyDistance'].forEach(id=>{const el=document.getElementById(id);if(el)el.textContent=km.toFixed(1)+' km'})}function drawMaps(events=[]){",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "Object.assign(route,r);",
    "Object.assign(route,r);updateRouteDistance();",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "setupMap('homeMap');setupMap('activeMap');setupMap('resultMap');",
    "setupMap('homeMap');setupMap('journeyMap');setupMap('activeMap');setupMap('resultMap');",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "function formatTime(seconds){",
    "function showReward(p){if(rewardShown||!p.co2)return;rewardShown=true;const reduction=Math.max(0,Number(p.co2.reduction_co2e_g||0));const earned=Math.floor(reduction/TOKEN_GRAMS_PER_TOKEN);const previous=tokenBalance;tokenBalance+=earned;localStorage.setItem('canopyTokenBalance',String(tokenBalance));let history=[];try{history=JSON.parse(localStorage.getItem('canopyTokenHistory')||'[]')}catch(e){history=[]}history.unshift({earned,reduction,date:new Date().toLocaleString('ko-KR')});localStorage.setItem('canopyTokenHistory',JSON.stringify(history.slice(0,20)));document.getElementById('tokenEarned').textContent='+'+earned+' Token';document.getElementById('rewardNote').textContent='CO2 감축량 '+reduction.toFixed(1)+' g 기준 · 10 g당 1 Token';document.getElementById('tokenBalance').textContent=previous;showScreen('reward');let current=previous;const started=performance.now();const tick=(now)=>{const progress=Math.min(1,(now-started)/800);current=Math.round(previous+(tokenBalance-previous)*progress);document.getElementById('tokenBalance').textContent=current;if(progress<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)}function formatTime(seconds){",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "if(currentScreen==='active')showScreen('result')}",
    "if(currentScreen==='active'){showScreen('result');setTimeout(()=>showReward(p),650)}}",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    "async function startTrip(){showScreen('active');",
    "async function startTrip(){rewardShown=false;showScreen('active');",
)
MOBILE_APP_HTML = MOBILE_APP_HTML.replace(
    '</section>\n</div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"',
    '</section><section id="mypage" class="screen profile-screen"><h2>마이페이지</h2><p class="muted">이번 데모에서 쌓은 Canopy Token을 확인할 수 있어요.</p><div class="profile-card"><div class="eyebrow">현재 보유 Token</div><div class="profile-token" id="myTokenBalance">0 Token</div></div><div class="profile-card"><div class="eyebrow">Token 받은 내역</div><div id="myRewardHistory"><p class="muted">아직 받은 Token이 없어요.</p></div></div></section><nav class="bottom-nav" aria-label="앱 메뉴"><button data-tab="home" onclick="navigateTab(\'home\')"><span>⌂</span>홈</button><button data-tab="journey" onclick="navigateTab(\'journey\')"><span>●</span>여정</button><button data-tab="mypage" onclick="navigateTab(\'mypage\')"><span>○</span>마이페이지</button></nav></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"',
)


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
        self._last_window_bucket = -1
        self._live_inference_enabled = False
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
            self._last_window_bucket = -1
            self._live_inference_enabled = speed != "instant"
            self.thread = Thread(target=self._run, args=(rows,), daemon=True)
            self.thread.start()

    def _run(self, rows: list[dict[str, Any]]) -> None:
        assert self.engine is not None
        result = self.engine.stream(rows, on_update=self._on_update)
        with self.lock:
            self.replay.update({"status": result.status, "accepted": sum(item.decision.accepted for item in result.updates), "rejected": sum(not item.decision.accepted for item in result.updates)})
            stopped = result.status == "STOPPED"
            if stopped and len(result.session.events) < 2:
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
        inference_events = None
        with self.lock:
            self.events.append(item)
            if self._live_inference_enabled and event is not None and update.decision.accepted and self.engine is not None:
                session = self.engine.ingestor.sessions.get(event.trip_id)
                if session and len(session.events) >= 2:
                    elapsed_bucket = int((event.timestamp - session.events[0].timestamp).total_seconds() // 120)
                    if elapsed_bucket > self._last_window_bucket:
                        self._last_window_bucket = elapsed_bucket
                        inference_events = list(session.events)
        if inference_events is not None:
            try:
                windows = infer_windows(
                    inference_events,
                    model_path=ROOT / "models/mobility_recognition/geolife_hardened_120s_purity_090.joblib",
                    window_seconds=120,
                )
                payload = [
                    {
                        "window_start": window.window_start.isoformat(),
                        "window_end": window.window_end.isoformat(),
                        "status": window.status,
                        "predicted_mode": window.predicted_mode,
                        "confidence": window.confidence,
                        "probabilities": window.probabilities,
                        "features": window.features,
                    }
                    for window in windows
                ]
                with self.lock:
                    self.window_predictions = payload
            except Exception:
                pass

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            live_events = []
            if self.engine and self.fixture:
                session = self.engine.ingestor.sessions.get(next(iter(self.engine.ingestor.sessions), ""))
                live_events = session.events if session else []
            live_distance = trajectory_distance_km(live_events) if len(live_events) >= 2 else 0.0
            return {"status": self.status, "view_mode": self.view_mode, "fixture": self.fixture, "replay": dict(self.replay), "pipeline": self.pipeline, "window_predictions": list(self.window_predictions), "events": list(self.events), "live_distance_km": live_distance, "raw_debug": {"event_count": len(self.events), "accepted_count": sum(bool(event["accepted"]) for event in self.events), "rejected_count": sum(not bool(event["accepted"]) for event in self.events)}}


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
    if not DEFAULT_MOCK.is_file():
        return None
    rows = read_replay_csv(DEFAULT_MOCK)
    events = [validate_gps_event(row).event for row in rows]
    valid_events = [event for event in events if event is not None]
    return build_expected_features(valid_events).features


def _baseline_payload() -> dict[str, object]:
    """Return the existing KTDB model output for the pre-trip card."""

    if not DEFAULT_KTDB_SAMPLE.is_file():
        return {"status": "WAITING", "reason": "existing KTDB processed sample is unavailable"}
    model = ROOT / "models/expected_behaviour/ktdb_population_baseline.pkl"
    if not model.is_file():
        return {"status": "WAITING", "reason": "existing KTDB model artifact is unavailable"}
    rows = read_replay_csv(DEFAULT_MOCK)
    events = [validate_gps_event(row).event for row in rows]
    valid_events = [event for event in events if event is not None]
    scenario = build_expected_features(valid_events)
    prediction = predict_expected_behaviour(pd.DataFrame([scenario.features]), model_path=model).iloc[0]
    return {
        "status": "READY",
        "predicted_mode": str(prediction["predicted_mode"]),
        "probabilities": {mode: float(prediction[f"{mode}_probability"]) for mode in ("walk", "bike", "car", "bus", "rail")},
        "source": "existing KTDB population baseline model",
        "features": scenario.features,
        "provenance": scenario.provenance,
    }


def _route_payload() -> dict[str, object]:
    """Read displayed origin/destination points from the supplied GPS CSV."""

    if not DEFAULT_MOCK.is_file():
        return {"status": "WAITING"}
    rows = read_replay_csv(DEFAULT_MOCK)
    if not rows:
        return {"status": "WAITING"}
    return {
        "status": "READY",
        "origin": {"label": "서울 영등포구 버드나루로10길 7", "latitude": float(rows[0]["latitude"]), "longitude": float(rows[0]["longitude"])},
        "destination": {"label": "Microsoft Korea · 서울 종로구 종로1길 50", "latitude": float(rows[-1]["latitude"]), "longitude": float(rows[-1]["longitude"])},
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: object, content_type: str = "application/json") -> None:
        body = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            # 브라우저 새로고침이나 요청 취소로 소켓이 먼저 닫힐 수 있다.
            # 해당 상황은 서버 오류가 아니므로 traceback 없이 응답만 종료한다.
            return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, MOBILE_APP_HTML, "text/html")
        elif path == "/api/fixtures":
            fixture_names = sorted(path.name for path in FIXTURE_DIR.glob("*.csv"))
            if DEFAULT_MOCK.is_file():
                fixture_names.insert(0, "mock/" + DEFAULT_MOCK.name)
            self._send(200, fixture_names)
        elif path == "/api/baseline":
            self._send(200, _baseline_payload())
        elif path == "/api/route":
            self._send(200, _route_payload())
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
