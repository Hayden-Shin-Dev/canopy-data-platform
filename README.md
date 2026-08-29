# Canopy Data Platform

## 프로젝트 목적

Canopy는 친환경 이동 자체를 보상하는 것이 아니라, 일반적으로 예상되는 이동행동과 실제 이동행동의 차이를 비교해 저탄소 방향의 Behaviour Shift를 측정하는 프로젝트입니다.

## 전체 구조

- KTDB: Expected Behaviour / Population Baseline
- GeoLife: Mobility Recognition Model 학습
- Emission Factors: 교통수단별 CO2 환산 기준
- Transit Context: GPS만으로 구분하기 어려운 bus/car 등의 판단 보조
- Realtime GPS: iOS GPS 수집과 Streaming
- Integration: Expected Behaviour와 Actual Behaviour 비교, CO2 Reduction 및 Reward 계산

## 현재 진행 상태

- KTDB Population Baseline v1 완료
- GeoLife Mobility Recognition v1 완료
- Emission Factors v1 완료
- Transit Context 서울 POC 완료
- Integration v1 완료
- iPhone 호환 GPS Event Contract, Replay Engine, Local Test UI 준비
- Integration validation: 192 tests passed

## 실행 순서

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant --pipeline
python scripts/run_integration_ui.py
pytest -q
```

Local UI는 `http://127.0.0.1:8765`에서 확인합니다. 상세 결과는 [Integration validation](reports/integration/FINAL_INTEGRATION_VALIDATION.md), iPhone 연동 규격은 [GPS Event Contract](docs/integration/GPS_EVENT_CONTRACT.md)를 참고합니다.

## Branch

- `main`: 전체 프로젝트 통합 상태
- `dev/ktdb-v1`: KTDB Population Baseline
- `dev/geolife-v1`: GeoLife Mobility Recognition
- `dev/emission-factors-v1`: Emission Factors
- `dev/transit-context-v1`: 서울 Transit Context POC
- `dev/integration-v1`: GPS Replay와 Expected/Actual Behaviour Integration

대용량 raw data, generated processed data, model artifact, `.env`는 Git에 커밋하지 않고 로컬에서 재생성·관리합니다.
