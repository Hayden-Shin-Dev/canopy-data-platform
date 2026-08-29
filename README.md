# Canopy Data Platform

## 프로젝트 목적

Canopy는 친환경 이동 자체를 보상하는 것이 아니라, 일반적으로 예상되는 이동행동과 실제 이동행동의 차이를 비교해 저탄소 방향의 Behaviour Shift를 측정하는 프로젝트입니다.

## 전체 구조

- KTDB: Expected Behaviour와 Population Baseline
- GeoLife: Mobility Recognition Model 학습
- Emission Factors: 교통수단별 CO2 환산 기준
- Transit Context: GPS만으로 구분하기 어려운 bus와 car 등의 판단 보조
- Realtime GPS: iOS GPS 수집과 Streaming
- Integration: Expected Behaviour와 Actual Behaviour 비교, CO2 Reduction 및 Reward 계산

## 현재 진행 상태

- KTDB Population Baseline v1 완료
- GeoLife Mobility Recognition v1 완료
- Emission Factors v1 완료
- Transit Context 서울 POC 완료
- Integration v1 완료
- iPhone 호환 GPS Event Contract, Replay Engine, Local User Mode 준비
- Integration validation: 201 tests passed

## 실행 순서

저장소 루트에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py --speed instant --pipeline
python scripts/evaluate_mock_trip.py
python scripts/run_integration_ui.py
pytest -q --disable-warnings
```

Local UI는 `http://127.0.0.1:8765`에서 확인합니다. 지도 Tile을 보려면 인터넷 연결이 필요합니다.

Integration 실행 방법과 사용자 화면은 [Integration branch README](https://github.com/Hayden-Shin-Dev/canopy-data-platform/tree/dev/integration-v1)에서 확인할 수 있습니다. 실제 확인 화면은 [Home](reports/integration/screenshots/home.png), [Active](reports/integration/screenshots/active.png), [Result](reports/integration/screenshots/result.png)입니다.

## 주요 문서

- [Integration validation](reports/integration/FINAL_INTEGRATION_VALIDATION.md)
- [GPS Event Contract](docs/integration/GPS_EVENT_CONTRACT.md)
- [iPhone handoff](docs/integration/IPHONE_HANDOFF.md)
- [Integration branch 실행 안내](https://github.com/Hayden-Shin-Dev/canopy-data-platform/tree/dev/integration-v1)

## Branch

- `main`: 전체 프로젝트 통합 상태
- `dev/ktdb-v1`: KTDB Population Baseline
- `dev/geolife-v1`: GeoLife Mobility Recognition
- `dev/emission-factors-v1`: Emission Factors
- `dev/transit-context-v1`: 서울 Transit Context POC
- `dev/integration-v1`: GPS Replay와 Expected Behaviour, Actual Behaviour Integration

대용량 raw data, generated processed data, model artifact, `.env`는 Git에 커밋하지 않고 로컬에서 재생성과 검증을 진행합니다.
