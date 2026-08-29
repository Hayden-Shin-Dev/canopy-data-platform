# Integration validation

검증일: 2026-08-29

현재 상태: **INCOMPLETE / LOCAL REPLAY READY**

GeoLife hardened model과 서울 Transit reference는 Desktop 경로에서 확인되지만, `data/processed.zip`에서 복원한 KTDB sample이 현재 model 계약과 달라 실제 full pipeline을 COMPLETE로 표시하지 않습니다. 없는 컬럼이나 값을 임의 생성하지 않았습니다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| iPhone-compatible GPS Event Contract | PASS | `docs/integration/GPS_EVENT_CONTRACT.md`, `tests/test_gps_contract.py` |
| GPS invalid/duplicate/out-of-order/gap/jump 처리 | PASS | `tests/test_integration_ingestion.py` |
| Haversine trajectory distance | PASS | `tests/test_integration_distance.py` |
| 120초 GeoLife window adapter | PASS (adapter) | `tests/test_integration_geolife_adapter.py` |
| GeoLife 실제 model artifact inference | PASS | `models/mobility_recognition/geolife_hardened_120s_purity_090.joblib` 존재, adapter 테스트 |
| Event-by-event replay와 1x/5x/10x/30x/Instant 선택 | PASS | `src/integration/replay.py`, `tests/test_integration_replay.py` |
| 서울 공식 bus reference 로딩 | PASS | `12,898` stops, `41,676` route-stop rows; `src/integration/pipeline.py` |
| 서울 subway/KORAIL reference 로딩 | PASS | `276` subway stations, `202` KORAIL stations |
| Transit 실제 GPS+GeoLife full integration | NOT TESTED | GeoLife artifact 부재로 실행 불가 |
| KTDB 실제 model inference | FAIL | model은 존재하지만 복원된 sample에 `origin_x`, `origin_y`, `destination_x`, `destination_y`가 없어 계약 불일치 |
| Emission factor table/resolver | PASS | `40` normalized factors, 실제 bus 1 km 계산 `101.51` gCO2e |
| Probability-weighted Expected CO2와 음수 reduction 보존 | PASS | `tests/test_integration_emissions.py` |
| Local Test UI | PASS (replay/status) | `scripts/run_integration_ui.py`, `tests/test_integration_ui.py` |
| Full production pipeline replay | FAIL | KTDB model/sample 계약 불일치로 `FAIL` 분리 |
| 전체 관련 테스트 | PASS | `pytest -q` → `192 passed, 30 warnings` |

## 실행

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant
python scripts/run_integration_ui.py
pytest -q
```

GeoLife artifact를 repository의 문서화된 경로에 준비한 뒤 실제 canonical GPS trip과 KTDB `MODEL_FEATURES`를 넣어 full pipeline을 재검증해야 합니다. 그 전까지 이 branch의 상태는 COMPLETE가 아닙니다.
