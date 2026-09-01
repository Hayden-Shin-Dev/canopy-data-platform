# Canopy Data Platform

## 현재 Production Movement ML

AI-Hub 실제 한국 GPS를 primary benchmark로 사용합니다. 사용자 UID가 겹치지 않는 train/validation/test split을 유지하며, 현재 champion은 linked vehicle 10,000-file 보강을 포함한 120초 aggregate HistGradientBoosting입니다. Validation Accuracy 0.7242 / Macro F1 0.7305, Test Accuracy 0.7071 / Macro F1 0.6992를 기록했습니다.

`evaluation_dataset_v3`는 synthetic historical benchmark로 보존하지만 Production 모델 선택과 Release Gate에서는 제외합니다. 정책과 근거는 [v3 benchmark deprecation](docs/evaluation/V3_BENCHMARK_DEPRECATION.md)에 정리되어 있습니다. 기존 GeoLife 모델은 rollback artifact로 유지합니다.

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
- Integration validation: 전체 테스트 248 passed

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

AI-Hub Production 모델을 처음 준비하거나 다시 만들 때는 저장소 루트에서 다음 PowerShell 명령을 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_aihub_production.ps1
```

linked 차량 ZIP을 사용해 같은 후보를 다시 만들려면 다음처럼 실행합니다. ZIP은 로컬에만 두고, 기본 10,000개 파일을 train split에만 추가합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_aihub_production.ps1 `
  -VehicleArchives "C:\path\01.연계데이터_003.차량이동궤적_2.zip"
```

모델 파일은 용량 때문에 Git에 저장하지 않습니다. 생성된 `models/mobility_recognition/aihub_hist120.joblib`이 있으면 production 경로가 이를 사용하고, 없으면 기존 GeoLife rollback 모델을 사용합니다.

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
