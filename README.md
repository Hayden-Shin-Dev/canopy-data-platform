# Canopy Integration

Canopy는 iPhone에서 들어오는 GPS Event를 기존 Canopy 분석 pipeline에 연결해 출퇴근 이동을 확인하는 Integration 단계입니다. 사용자 화면에서는 이동을 시작하고, 이동 중 상태를 보고, 끝난 뒤 탄소 결과를 확인할 수 있습니다.

## 이번 단계에서 확인하는 것

- iPhone 형식의 GPS CSV를 기존 Replay Engine으로 읽습니다.
- 기존 120초 Window, GeoLife, Transit Context, KTDB, Emission 결과를 그대로 사용합니다.
- 사용자가 보는 화면은 지도 중심의 Home, Active Trip, Result 세 화면으로 나뉩니다.
- Developer Mode에서는 raw GPS와 Window, 모델 결과를 별도로 확인할 수 있습니다.

이번 단계에서는 모델이나 판정 규칙을 새로 만들지 않습니다. Mock의 정답 파일도 평가용으로만 읽으며 inference 입력으로 사용하지 않습니다.

## 준비

저장소 루트에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
```

실행 전 KTDB, GeoLife, Transit reference와 모델 파일이 로컬에 있어야 합니다. 원본 대용량 데이터와 `.env`는 Git에 올리지 않습니다.

## 가장 빠른 실행 방법

먼저 전체 산출물과 fixture 상태를 확인합니다.

```powershell
python scripts/validate_integration_artifacts.py
```

Mock GPS를 기존 production pipeline으로 재생합니다.

```powershell
python scripts/replay_integration.py --speed instant --pipeline
```

재생이 끝나면 평가용 Ground Truth와 비교할 수 있습니다.

```powershell
python scripts/evaluate_mock_trip.py
```

## 사용자 화면 실행

다른 PowerShell 창에서 다음 명령을 실행합니다.

```powershell
python scripts/run_integration_ui.py
```

브라우저에서 `http://127.0.0.1:8765`를 엽니다.

1. Home에서 출발지와 도착지, KTDB Population Baseline을 확인합니다.
2. `출근 시작하기`를 누르면 `mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`가 Replay됩니다.
3. Active Trip에서 현재 위치, 지나온 경로, 이동 시간과 거리를 확인합니다.
4. `이동 종료`를 누르거나 Replay가 끝날 때까지 기다리면 Result 화면에서 기존 pipeline의 실제 CO2 결과를 확인합니다.
5. `Developer`를 누르면 fixture, raw GPS, Window prediction, Transit와 pipeline 결과를 볼 수 있습니다.

UI는 OpenStreetMap Tile을 사용하므로 지도 확인 시 인터넷 연결이 필요합니다. 포트를 바꾸려면 다음처럼 실행합니다.

```powershell
python scripts/run_integration_ui.py --port 8772
```

## 검증 화면

400 x 820 크기의 브라우저에서 실제로 확인한 화면입니다.

### Home

출발지와 도착지 Marker, 실제 OSM 지도, KTDB Baseline 확률을 표시합니다.

![Home 화면](reports/integration/screenshots/home.png)

### Active Trip

Replay Event가 들어올 때 현재 위치 Marker와 누적 Polyline이 갱신됩니다. 이동수단 문구는 기존 GeoLife 결과를 그대로 표시합니다.

![Active 화면](reports/integration/screenshots/active.png)

### Result

기존 Full Pipeline에서 나온 거리, 시간, Expected CO2, Actual CO2, CO2 Reduction을 표시합니다.

![Result 화면](reports/integration/screenshots/result.png)

현재 제공된 Mock에서는 실제 모델 결과가 `walk`, `bike`, `walk` 순서로 기록됩니다. Ground Truth의 `walk`, `rail`, `walk`에 맞추기 위한 보정은 하지 않습니다.

## 테스트

```powershell
pytest -q --disable-warnings
```

현재 UI 및 Integration 관련 테스트를 포함해 전체 테스트가 통과해야 합니다.

주요 결과 문서는 다음 위치에 있습니다.

- `reports/integration/FINAL_INTEGRATION_VALIDATION.md`
- `reports/integration/mock_trip_evaluation.json`
- `docs/integration/GPS_EVENT_CONTRACT.md`
- `docs/integration/IPHONE_HANDOFF.md`

## 주요 입력과 코드

- Mock 입력: `mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`
- Replay Engine: `src/integration/replay.py`
- 전체 pipeline 연결: `src/integration/pipeline.py`
- Local UI: `scripts/run_integration_ui.py`
- UI 테스트: `tests/test_integration_ui.py`

`main`은 전체 프로젝트 통합용으로 유지하고, 이 Branch의 README는 Integration과 Local User Mode 실행 방법을 설명하는 데 사용합니다.
