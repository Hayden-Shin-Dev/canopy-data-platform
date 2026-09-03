"use strict";

const MODE_META = {
  walk: { label: "도보", live: "지금은 걷는 중이에요", icon: "ph-person-simple-walk", color: "#07855f" },
  bike: { label: "자전거", live: "자전거로 이동 중이에요", icon: "ph-bicycle", color: "#ff4b4f" },
  car: { label: "자동차", live: "자동차로 이동 중이에요", icon: "ph-car", color: "#263d51" },
  bus: { label: "버스", live: "버스를 타셨네요", icon: "ph-bus", color: "#347bf4" },
  rail: { label: "철도", live: "지하철/철도로 이동 중이에요", icon: "ph-train", color: "#347bf4" },
};

const NAV_ITEMS = [
  ["home", "ph-house", "홈"],
  ["plan", "ph-signpost", "여정 계획"],
  ["start", "ph-fill ph-leaf", ""],
  ["complete", "ph-gift", "리워드"],
  ["profile", "ph-user", "마이페이지"],
];

const state = {
  screen: "home",
  baseline: null,
  route: null,
  snapshot: null,
  map: null,
  mapLine: null,
  routePreviewLine: null,
  routeBounds: null,
  currentMarker: null,
  originMarker: null,
  destinationMarker: null,
  tripStarted: false,
  resultStored: false,
  resultRenderKey: null,
  activeMode: null,
  pollTimer: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let payload;
  try { payload = await response.json(); } catch { payload = { error: `HTTP ${response.status}` }; }
  if (!response.ok || payload?.status === "FAIL") {
    throw new Error(payload?.error || payload?.reason || `요청 실패 (${response.status})`);
  }
  return payload;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

function buildNavigation() {
  $$(".bottom-nav").forEach(nav => {
    nav.innerHTML = NAV_ITEMS.map(([screen, icon, label], index) => {
      const center = index === 2 ? " center-action" : "";
      return `<button type="button" class="${center.trim()}" data-nav="${screen}" aria-label="${label || "여정 시작"}"><i class="${icon.startsWith("ph-fill") ? icon : `ph ${icon}`}"></i>${label ? `<span>${label}</span>` : ""}</button>`;
    }).join("");
  });
}

function showScreen(name, { updateUrl = true } = {}) {
  if (!document.getElementById(name)) name = "home";
  state.screen = name;
  $$(".app-screen").forEach(screen => screen.classList.toggle("is-active", screen.id === name));
  $$('[data-nav]').forEach(button => {
    const selected = button.dataset.nav === name || (name === "active" && button.dataset.nav === "plan");
    button.classList.toggle("is-active", selected);
  });
  if (name === "active") window.setTimeout(() => {
    state.map?.invalidateSize();
    if (state.map && state.routeBounds) state.map.fitBounds(state.routeBounds, { padding: [28, 96], maxZoom: 15, animate: true });
  }, 80);
  if (name === "profile") renderProfile();
  if (updateUrl) history.replaceState(null, "", `${location.pathname}?screen=${name}`);
}

function modeMeta(mode) { return MODE_META[mode] || { label: mode || "판정 중", live: "이동 패턴을 확인하고 있어요", icon: "ph-radar", color: "#347bf4" }; }
function journeyIcon(mode) { return { walk: "ph-person-simple-walk", bike: "ph-bicycle", car: "ph-car", bus: "ph-bus", rail: "ph-train" }[mode] || "ph-navigation-arrow"; }
function renderJourneyProgress(mode, ratio = 0) {
  const percent = `${Math.max(0, Math.min(100, Number(ratio) * 100))}%`;
  ["start", "active"].forEach(prefix => {
    const traveler = $(`#${prefix}-traveler`);
    const fill = $(`#${prefix}-journey-progress .progress-fill`);
    if (!traveler) return;
    traveler.className = `journey-traveler ${mode || "unknown"}`;
    traveler.innerHTML = `<i class="ph-fill ${journeyIcon(mode)}"></i>`;
    traveler.style.left = percent;
    if (fill) fill.style.width = percent;
  });
}
function number(value, digits = 1) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "-"; }

function durationText(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return hours ? `${hours}시간 ${minutes}분` : `${minutes}분`;
}

function clockText(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function elapsedSeconds(events = []) {
  const accepted = events.filter(event => event.accepted && event.timestamp);
  if (accepted.length < 2) return 0;
  return Math.max(0, (new Date(accepted.at(-1).timestamp) - new Date(accepted[0].timestamp)) / 1000);
}

function loadHistory() {
  try { return JSON.parse(localStorage.getItem("canopy.tripHistory") || "[]"); }
  catch { return []; }
}

function saveHistory(history) { localStorage.setItem("canopy.tripHistory", JSON.stringify(history.slice(0, 20))); }

function renderHistorySummary() {
  const history = loadHistory();
  const reductionG = history.reduce((sum, trip) => sum + Number(trip.reductionG || 0), 0);
  const distanceKm = history.reduce((sum, trip) => sum + Number(trip.distanceKm || 0), 0);
  const durationSec = history.reduce((sum, trip) => sum + Number(trip.durationSec || 0), 0);
  const token = history.reduce((sum, trip) => sum + Number(trip.token || 0), 0);
  const monthKg = reductionG / 1000;
  const goalPercent = Math.min(100, monthKg / 20 * 100);
  $("#home-month-reduction").textContent = number(monthKg, 1);
  $("#home-week-distance").textContent = `${number(distanceKm, 1)} km`;
  $("#home-week-time").textContent = durationText(durationSec).replace("시간", "h ").replace("분", "m");
  $("#home-week-reduction").textContent = `${number(monthKg, 1)} kg`;
  $("#goal-percent").textContent = `${Math.round(goalPercent)}%`;
  $("#goal-current").textContent = number(monthKg, 1);
  $("#goal-progress").style.width = `${goalPercent}%`;
  $("#profile-token").textContent = `${token} Token`;
  $("#profile-trips").textContent = `${history.length}회`;
  $("#profile-distance").textContent = `${number(distanceKm, 1)} km`;
  $("#profile-reduction").textContent = `${number(monthKg, 1)} kg`;
  $("#cumulative-reduction").innerHTML = `${number(monthKg, 2)} kg CO<sub>2</sub>`;
  $("#tree-equivalent").textContent = `30년생 소나무 ${number(monthKg / 8.3, 2)}그루가 1년간 흡수하는 양`;
}

function renderProfile() {
  renderHistorySummary();
  const history = loadHistory();
  const container = $("#token-history");
  if (!history.length) {
    container.innerHTML = '<p class="empty-copy">여정을 완료하면 Token 적립 내역이 여기에 표시됩니다.</p>';
    return;
  }
  container.innerHTML = history.slice(0, 5).map(trip => `
    <article class="history-row">
      <span class="round-icon"><i class="ph-fill ph-coin"></i></span>
      <span><strong>친환경 여정 리워드</strong><small>${new Date(trip.createdAt).toLocaleString("ko-KR")}</small></span>
      <b>+${trip.token}</b>
    </article>`).join("");
}

function renderBaseline(payload) {
  if (payload?.status !== "READY") return;
  state.baseline = payload;
  const expectedG = Number(payload.expected_co2e_g || 0);
  const recommendedG = Number(payload.recommended_co2e_g || 0);
  const distanceKm = Number(payload.distance_km || 0);
  const durationSec = Number(payload.duration_sec || 0);
  const savingG = Math.max(0, expectedG - recommendedG);
  const savingPercent = expectedG ? savingG / expectedG * 100 : 0;
  $("#baseline-emission").textContent = expectedG ? `${number(expectedG / 1000, 2)}kg` : "계산 중";
  $("#start-baseline").textContent = expectedG ? `${number(expectedG / 1000, 2)} kg` : "계산 중";
  $("#recommended-duration").textContent = durationSec ? durationText(durationSec) : "시간 계산 중";
  $("#start-duration").textContent = durationSec ? durationText(durationSec) : "계산 중";
  $("#start-distance").textContent = distanceKm ? `${number(distanceKm, 1)} km` : "계산 중";
  $("#recommended-emission").textContent = recommendedG ? `${number(recommendedG / 1000, 2)} kg` : "계산 중";
  $("#start-target").textContent = recommendedG ? `${number(recommendedG / 1000, 2)} kg` : "계산 중";
  $("#start-saving-percent").textContent = expectedG ? `${number(savingPercent, 0)}% 절감 목표` : "실제 Baseline 계산 중";
  $("#plan-saving").textContent = expectedG ? `${number(savingG / 1000, 2)}kg` : "계산 중";
  $("#plan-saving-percent").textContent = expectedG ? `(${number(savingPercent, 0)}% 감소)` : "";
  $("#route-emission").textContent = recommendedG ? `${number(recommendedG / 1000, 2)}kg` : "계산 중";
  const maxG = Math.max(expectedG, recommendedG, 1);
  $("#baseline-bar").style.height = `${Math.max(12, expectedG / maxG * 52)}px`;
  $("#route-bar").style.height = `${Math.max(8, recommendedG / maxG * 52)}px`;
  renderBaselineDetails(payload.probabilities || {});
  // 출발 전에는 수단을 미리 정하지 않고, 실제 Window 판정이 들어온 뒤 아이콘을 표시합니다.
  renderJourneyProgress(null, 0);
}

function renderBaselineDetails(probabilities) {
  const labels = { walk: "도보", bike: "자전거", car: "자동차", bus: "버스", rail: "지하철·철도" };
  const icons = { walk: "ph-person-simple-walk", bike: "ph-bicycle", car: "ph-car", bus: "ph-bus", rail: "ph-train" };
  const rows = $("#baseline-mode-rows");
  if (!rows) return;
  rows.innerHTML = Object.entries(labels).map(([mode, label]) => {
    const percent = Math.max(0, Math.min(100, Number(probabilities[mode] || 0) * 100));
    return `<div class="baseline-mode-row"><span><i class="ph ${icons[mode]}"></i> ${label}</span><div class="baseline-mode-track"><b style="width:${percent.toFixed(2)}%"></b></div><strong>${percent.toFixed(1)}%</strong></div>`;
  }).join("");
}

function renderRoute(payload) {
  if (payload?.status !== "READY") return;
  state.route = payload;
  if (payload.origin?.label) $("#start-origin-address").textContent = payload.origin.label;
  if (payload.destination?.label) $("#start-destination-address").textContent = payload.destination.label;
  const activeAddress = document.querySelector(".active-header > p");
  if (activeAddress && payload.origin?.label && payload.destination?.label) {
    activeAddress.innerHTML = `<span class="route-address"><i class="ph-fill ph-house"></i>${payload.origin.label}</span><span class="route-address-separator" aria-hidden="true"></span><span class="route-address"><i class="ph-fill ph-buildings"></i>${payload.destination.label}</span>`;
  }
  const originButton = document.querySelector('[data-address-popover="origin"]');
  const destinationButton = document.querySelector('[data-address-popover="destination"]');
  if (originButton && payload.origin?.label) {
    originButton.dataset.address = payload.origin.label;
    originButton.title = payload.origin.label;
  }
  if (destinationButton && payload.destination?.label) {
    destinationButton.dataset.address = payload.destination.label;
    destinationButton.title = payload.destination.label;
  }
  const distanceKm = Number(payload.distance_km || 0);
  if (distanceKm) $("#start-distance").textContent = `${number(distanceKm, 1)} km`;
  ensureMap();
  const points = payload.polyline || [];
  if (state.map && points.length > 1) {
    const latLngs = points.map(point => [point.latitude, point.longitude]);
    state.routeBounds = L.latLngBounds(latLngs);
    state.routePreviewLine?.remove();
    state.routePreviewLine = L.polyline(latLngs, { color: "#b6c5bd", weight: 4, opacity: .75, dashArray: "5 8" }).addTo(state.map);
    addEndpointMarkers(latLngs[0], latLngs.at(-1));
    state.map.fitBounds(L.latLngBounds(latLngs), { padding: [28, 28] });
  }
}

function ensureMap() {
  if (state.map || typeof L === "undefined") return;
  state.map = L.map("active-map", { zoomControl: false, attributionControl: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap",
  }).addTo(state.map);
  state.map.setView([37.526, 126.94], 12);
}

function markerIcon(iconClass, className) {
  return L.divIcon({
    className: `canopy-marker ${className}`,
    html: `<i class="ph-fill ${iconClass}"></i>`,
    iconSize: [34, 34],
    iconAnchor: [17, 30],
  });
}

function addEndpointMarkers(origin, destination) {
  state.originMarker?.remove();
  state.destinationMarker?.remove();
  state.originMarker = L.marker(origin, { icon: markerIcon("ph-house", "origin-marker") }).addTo(state.map);
  state.destinationMarker = L.marker(destination, { icon: markerIcon("ph-buildings", "destination-marker") }).addTo(state.map);
}

function renderMap(events = []) {
  ensureMap();
  if (!state.map) return;
  const accepted = events.filter(event => event.accepted && Number.isFinite(Number(event.latitude)) && Number.isFinite(Number(event.longitude)));
  if (!accepted.length) return;
  const latLngs = accepted.map(event => [Number(event.latitude), Number(event.longitude)]);
  state.routePreviewLine?.setStyle({ opacity: .2 });
  if (!state.mapLine) state.mapLine = L.polyline(latLngs, { color: "#2878f4", weight: 5, opacity: .95 }).addTo(state.map);
  else state.mapLine.setLatLngs(latLngs);
  const current = latLngs.at(-1);
  if (!state.currentMarker) state.currentMarker = L.marker(current, { icon: markerIcon("ph-navigation-arrow", "current-marker") }).addTo(state.map);
  else state.currentMarker.setLatLng(current);
  if (accepted.length === 1 && state.routeBounds) state.map.fitBounds(state.routeBounds, { padding: [28, 96], maxZoom: 15, animate: true });
  else if (accepted.length % 6 === 0) state.map.panTo(current, { animate: true, duration: .4 });
}

function latestMode(snapshot) {
  const window = (snapshot.window_predictions || []).filter(row => row.status !== "FAIL").at(-1);
  if (!window) return { mode: null, confidence: null, line: null };
  return { mode: window.predicted_mode, confidence: window.confidence, line: null };
}

function renderActive(snapshot) {
  const prediction = latestMode(snapshot);
  const meta = modeMeta(prediction.mode);
  const icon = $("#active-mode-icon");
  if (state.activeMode !== prediction.mode) {
    state.activeMode = prediction.mode;
    icon.style.background = meta.color;
    icon.innerHTML = `<i class="ph ${meta.icon}"></i>`;
    $("#active-mode-title").textContent = meta.live;
  }
  $("#active-mode-detail").textContent = prediction.mode
    ? `현재 모델 confidence ${Math.round(Number(prediction.confidence || 0) * 100)}%`
    : "120초 Window 판정을 기다리는 중";
  $("#active-time").textContent = clockText(elapsedSeconds(snapshot.events));
  $("#active-distance").textContent = `${number(snapshot.live_distance_km || 0, 2)} km`;
  const routeDistance = Number(state.route?.distance_km || 0);
  renderJourneyProgress(prediction.mode, routeDistance ? Number(snapshot.live_distance_km || 0) / routeDistance : 0);
  renderMap(snapshot.events);
}

function segmentLabel(segment) {
  if (segment.mode === "rail" && segment.matched_subway_line) return `${segment.matched_subway_line}호선`;
  return modeMeta(segment.mode).label;
}

function resultDuration(pipeline) {
  return (pipeline.actual_behaviour?.segments || []).reduce((sum, segment) => sum + Number(segment.duration_sec || 0), 0);
}

function storeResult(pipeline, fixture) {
  if (state.resultStored || pipeline?.status !== "PASS") return;
  const key = `${fixture}:${pipeline.accepted_event_count}:${number(pipeline.distance_km, 4)}`;
  const history = loadHistory();
  if (history.some(item => item.key === key)) { state.resultStored = true; return; }
  const reductionG = Math.max(0, Number(pipeline.co2?.reduction_co2e_g || 0));
  history.unshift({
    key,
    createdAt: new Date().toISOString(),
    reductionG,
    distanceKm: Number(pipeline.distance_km || 0),
    durationSec: resultDuration(pipeline),
    token: Math.floor(reductionG / 10),
    modeSequence: pipeline.actual_behaviour?.mode_sequence || [],
  });
  saveHistory(history);
  state.resultStored = true;
  renderHistorySummary();
}

function renderResult(snapshot) {
  const pipeline = snapshot.pipeline || {};
  if (pipeline.status !== "PASS") return;
  const actualG = Number(pipeline.co2?.actual_co2e_g || 0);
  const expectedG = Number(pipeline.co2?.expected_co2e_g || 0);
  const reductionG = Number(pipeline.co2?.reduction_co2e_g || 0);
  const reductionPercent = expectedG ? reductionG / expectedG * 100 : 0;
  const segments = pipeline.actual_behaviour?.segments || [];
  const renderKey = `${snapshot.fixture || ""}:${pipeline.accepted_event_count || 0}:${number(pipeline.distance_km, 4)}:${actualG}:${segments.length}`;
  if (state.resultRenderKey === renderKey) return;
  state.resultRenderKey = renderKey;
  const modes = segments.map(segmentLabel);
  const token = Math.max(0, Math.floor(reductionG / 10));
  $("#result-actual").textContent = `${number(actualG / 1000, 2)} kg`;
  $("#result-expected").textContent = `${number(expectedG / 1000, 2)} kg`;
  $("#result-reduction").textContent = `${number(reductionG / 1000, 2)} kg 절감`;
  $("#result-percent").textContent = `(${number(reductionPercent, 0)}% 감소)`;
  $("#result-progress-bar").style.width = `${Math.max(0, Math.min(100, reductionPercent))}%`;
  $("#result-time").textContent = durationText(resultDuration(pipeline));
  $("#result-distance").textContent = `${number(pipeline.distance_km, 1)} km`;
  $("#result-modes").textContent = modes.join(" → ") || "-";
  $("#result-token").textContent = `+${token} Token`;
  const modeIcons = { walk: "ph-person-simple-walk", bike: "ph-bicycle", car: "ph-car", bus: "ph-bus", rail: "ph-train" };
  $("#result-segments").innerHTML = segments.map(segment => `<div class="segment-row"><span class="segment-icon"><i class="ph-fill ${modeIcons[segment.mode] || "ph-navigation-arrow"}"></i></span><span class="segment-main"><strong>${segmentLabel(segment)}</strong><small>${durationText(segment.duration_sec)} · ${number(segment.distance_km, 2)} km</small></span><span class="segment-emission"><b>${number(segment.co2e_g, 1)} g</b> CO<sub>2</sub></span></div>`).join("");
  $("#result-segments").classList.toggle("is-visible", segments.length > 0);
  storeResult(pipeline, snapshot.fixture);
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  renderActive(snapshot);
  renderResult(snapshot);
  $("#developer-json").textContent = JSON.stringify(snapshot, null, 2);
  if (state.tripStarted && snapshot.status === "PASS" && state.screen === "active") {
    showScreen("complete");
    showToast("여정 분석과 탄소 계산이 완료됐어요.");
  }
  if (snapshot.status === "FAIL") showToast(snapshot.pipeline?.reason || "여정 처리 중 오류가 발생했습니다.");
}

async function pollStatus() {
  try { renderSnapshot(await api("/api/status")); }
  catch (error) { console.error(error); }
}

async function startTrip({ developer = false } = {}) {
  try {
    state.resultStored = false;
    state.resultRenderKey = null;
    state.activeMode = null;
    state.tripStarted = true;
    state.mapLine?.remove(); state.mapLine = null;
    state.currentMarker?.remove(); state.currentMarker = null;
    const fixture = developer ? $("#fixture").value : "mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv";
    const speed = developer ? $("#speed").value : "30";
    await api("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fixture, speed, view_mode: developer ? "developer" : "user" }),
    });
    showScreen("active");
  } catch (error) { showToast(error.message); }
}

async function stopTrip() {
  try {
    await api("/api/stop", { method: "POST" });
    showToast("이동을 종료하고 결과를 계산하고 있어요.");
  } catch (error) { showToast(error.message); }
}

async function runAIHubReplay() {
  const output = $("#aihub-result");
  output.textContent = "실제 Test GPS를 처리하고 있습니다...";
  try {
    const payload = await api("/api/aihub/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ replay_id: $("#aihub-replay").value, source_root: $("#aihub-root").value, speed: $("#speed").value }),
    });
    output.textContent = JSON.stringify(payload, null, 2);
  } catch (error) { output.textContent = `FAIL\n${error.message}`; }
}

function bindInteractions() {
  document.addEventListener("click", async event => {
    const endpoint = event.target.closest("[data-address-popover]");
    const addressPopover = $("#active-address-popover");
    if (endpoint && addressPopover) {
      const destination = endpoint.dataset.addressPopover === "destination";
      $("#active-address-kind").textContent = destination ? "목적지" : "출발지";
      $("#active-address-value").textContent = endpoint.dataset.address || "주소 정보를 불러오는 중";
      addressPopover.classList.toggle("destination", destination);
      addressPopover.hidden = false;
      return;
    }
    if (addressPopover && !event.target.closest("#active-address-popover")) addressPopover.hidden = true;
    const nav = event.target.closest("[data-nav]");
    if (nav) { showScreen(nav.dataset.nav); return; }
    const action = event.target.closest("[data-action]");
    if (action) { showScreen(action.dataset.action); return; }
    const filter = event.target.closest("[data-filter]");
    if (filter) {
      $$("[data-filter]").forEach(button => button.classList.toggle("is-selected", button === filter));
      const selected = filter.dataset.filter;
      $$(".route-card").forEach(card => card.hidden = selected !== "recommended" && card.dataset.route !== selected);
      return;
    }
    const route = event.target.closest("[data-route]");
    if (route) {
      $$("[data-route]").forEach(card => { card.classList.toggle("recommended", card === route); card.setAttribute("aria-pressed", card === route ? "true" : "false"); });
    }
  });
  const baselineToggle = $("#baseline-detail-toggle");
  baselineToggle?.addEventListener("click", () => {
    const panel = $("#baseline-detail-panel");
    if (!panel) return;
    const open = panel.hidden;
    panel.hidden = !open;
    baselineToggle.setAttribute("aria-expanded", String(open));
  });
  const resultModeToggle = $("#result-mode-toggle");
  resultModeToggle?.addEventListener("click", () => {
    const list = $("#result-segments");
    if (!list) return;
    const open = !list.classList.contains("is-visible");
    list.classList.toggle("is-visible", open);
    resultModeToggle.setAttribute("aria-expanded", String(open));
  });
  $("#start-trip-button").addEventListener("click", () => startTrip());
  $("#developer-start").addEventListener("click", () => startTrip({ developer: true }));
  $("#stop-trip-button").addEventListener("click", stopTrip);
  $("#aihub-start").addEventListener("click", runAIHubReplay);
  $("#open-developer").addEventListener("click", () => showScreen("developer"));
  $("#active-menu-button").addEventListener("click", () => $("#active-menu").showModal());
  $("[data-close-dialog]").addEventListener("click", () => $("#active-menu").close());
  $("#pause-button").addEventListener("click", async () => { try { await api("/api/pause", { method: "POST" }); $("#active-menu").close(); showToast("여정을 일시정지했어요."); } catch (error) { showToast(error.message); } });
  $("#resume-button").addEventListener("click", async () => { try { await api("/api/resume", { method: "POST" }); $("#active-menu").close(); showToast("여정을 다시 시작했어요."); } catch (error) { showToast(error.message); } });
  $("#zoom-in-button").addEventListener("click", () => state.map?.zoomIn());
  $("#zoom-out-button").addEventListener("click", () => state.map?.zoomOut());
  $("#locate-button").addEventListener("click", () => { const point = state.currentMarker?.getLatLng(); if (point) state.map.setView(point, 16, { animate: true }); });
  $("#share-result-button").addEventListener("click", async () => {
    const text = `Canopy 여정 결과: ${$("#result-reduction").textContent}`;
    try {
      if (navigator.share) await navigator.share({ title: "Canopy 여정 결과", text });
      else { await navigator.clipboard.writeText(text); showToast("결과를 클립보드에 복사했어요."); }
    } catch (error) { if (error.name !== "AbortError") showToast("공유 기능을 사용할 수 없습니다."); }
  });
}

async function initData() {
  const [fixtures, manifest, baseline, route, snapshot] = await Promise.allSettled([
    api("/api/fixtures"), api("/api/aihub/manifest"), api("/api/baseline"), api("/api/route"), api("/api/status"),
  ]);
  if (fixtures.status === "fulfilled") {
    try { $("#fixture").innerHTML = fixtures.value.map(value => `<option value="${value}">${value}</option>`).join(""); }
    catch (error) { console.error("Canopy fixture render failed", error); }
  }
  if (manifest.status === "fulfilled") {
    try { $("#aihub-replay").innerHTML = (manifest.value.trajectories || []).map(row => `<option value="${row.replay_id}">${row.replay_id} · ${row.ground_truth}</option>`).join(""); }
    catch (error) { console.error("Canopy replay manifest render failed", error); }
  }
  // 선택적 요청 하나가 실패해도 기준선과 경로 화면은 계속 사용할 수 있어야 합니다.
  const coreRenderErrors = [];
  if (baseline.status === "fulfilled") {
    try { renderBaseline(baseline.value); } catch (error) { coreRenderErrors.push("baseline"); console.error("Canopy baseline render failed", error); }
  }
  if (route.status === "fulfilled") {
    try { renderRoute(route.value); } catch (error) { coreRenderErrors.push("route"); console.error("Canopy route render failed", error); }
  }
  if (snapshot.status === "fulfilled") {
    try { renderSnapshot(snapshot.value); } catch (error) { console.error("Canopy status render failed", error); }
  }
  if (baseline.status !== "fulfilled" || route.status !== "fulfilled" || coreRenderErrors.length) {
    console.warn("Canopy core startup data unavailable", {
      baseline: baseline.status,
      route: route.status,
      renderErrors: coreRenderErrors,
    });
    showToast("기준선 또는 경로 데이터를 불러오지 못했습니다.");
  }
}

async function init() {
  buildNavigation();
  bindInteractions();
  renderHistorySummary();
  // Show the branded intro only for a fresh root visit. Deep links (?screen=...) remain direct.
  const requested = new URLSearchParams(location.search).get("screen") || "landing";
  showScreen(requested, { updateUrl: false });
  try { await initData(); } catch (error) { console.error(error); showToast("초기 데이터를 불러오지 못했습니다."); }
  state.pollTimer = window.setInterval(pollStatus, 1000);
}

document.addEventListener("DOMContentLoaded", init);
