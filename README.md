# Canopy Integration

이 Branch는 iPhone 호환 GPS Event를 같은 ingestion 경로로 받아 Expected Behaviour와 Actual Behaviour를 비교하는 local integration 단계입니다.

## 구성

- GPS Event Contract와 품질 검증
- 120초 GeoLife Window adapter와 기존 model 호출
- 서울 Bus/Subway/KORAIL Transit Context
- KTDB Expected Behaviour 확률
- Emission Factor 기반 Expected/Actual CO2와 Reduction
- event-by-event Replay Engine과 dependency-free Local Test UI

## 실행

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant
python scripts/run_integration_ui.py
pytest -q
```

브라우저 UI는 `http://127.0.0.1:8765`에서 확인합니다. KTDB Expected Behaviour를 실행하려면 `src/ktdb/schema.py`의 `MODEL_FEATURES`를 모두 포함한 JSON 입력이 필요합니다.

## 현재 상태

**INCOMPLETE / LOCAL REPLAY READY**

Contract, ingestion, replay, 서울 reference loader, KTDB sample inference, Emission 계산과 테스트는 준비되어 있습니다. GeoLife hardened model artifact가 로컬에 없어 실제 full production pipeline은 아직 PASS가 아닙니다. 상세 근거는 [FINAL_INTEGRATION_VALIDATION.md](reports/integration/FINAL_INTEGRATION_VALIDATION.md)를 확인합니다.

## 문서

- [GPS Event Contract](docs/integration/GPS_EVENT_CONTRACT.md)
- [iPhone handoff](docs/integration/IPHONE_HANDOFF.md)
- [Manual test guide](reports/integration/MANUAL_TEST_GUIDE.md)
- [Final validation](reports/integration/FINAL_INTEGRATION_VALIDATION.md)
