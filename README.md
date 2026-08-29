# Canopy Integration

이 Branch는 iPhone 호환 GPS Event를 같은 ingestion 경로로 받아 Expected Behaviour와 Actual Behaviour를 비교하는 local integration 단계입니다.

## 구성

- GPS Event Contract와 품질 검증
- 120초 GeoLife Window와 실제 model inference
- 서울 Bus/Subway/KORAIL Transit Context
- KTDB Expected Behaviour 확률
- Emission Factor 기반 Expected/Actual CO2와 Reduction
- event-by-event Replay Engine과 Local Test UI

## 현재 상태

**INTEGRATION COMPLETE / LOCAL REPLAY READY**

Desktop 저장소의 실제 model, KTDB 재생성 dataset, 서울 Transit reference로 6개 fixture를 검증했습니다. 부족한 GPS는 `COLLECTING`으로 남기며 임의 결과를 만들지 않습니다.

## 실행

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant --pipeline
python scripts/run_integration_ui.py
pytest -q
```

UI: `http://127.0.0.1:8765`

자세한 결과는 [FINAL_INTEGRATION_VALIDATION.md](reports/integration/FINAL_INTEGRATION_VALIDATION.md), 계약은 [GPS_EVENT_CONTRACT.md](docs/integration/GPS_EVENT_CONTRACT.md), iPhone 연동은 [IPHONE_HANDOFF.md](docs/integration/IPHONE_HANDOFF.md)를 확인합니다.
