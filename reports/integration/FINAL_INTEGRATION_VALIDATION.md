# Integration validation

검증일: 2026-08-29

현재 상태: **INTEGRATION COMPLETE / LOCAL REPLAY READY**

Desktop 저장소의 실제 model·reference·KTDB 재생성 산출물로 검증했습니다. 원본 raw는 수정하지 않았습니다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| iPhone-compatible GPS Event Contract | PASS | `docs/integration/GPS_EVENT_CONTRACT.md`, `tests/test_gps_contract.py` |
| GPS invalid/duplicate/out-of-order/gap/jump 처리 | PASS | `tests/test_integration_ingestion.py` |
| Haversine trajectory distance | PASS | `tests/test_integration_distance.py` |
| 120초 GeoLife window와 실제 model inference | PASS | Desktop `models/mobility_recognition/geolife_hardened_120s_purity_090.joblib` |
| Event-by-event replay와 1x/5x/10x/30x/Instant | PASS | `src/integration/replay.py`, 6 fixtures |
| 서울 Bus reference | PASS | 12,898 stops, 41,676 route-stop rows |
| 서울 Subway/KORAIL reference | PASS | 276 / 202 stations |
| KTDB 실제 model inference | PASS | 재생성된 feature CSV와 `ktdb_population_baseline.pkl` |
| Emission factor table/resolver | PASS | 40 factors, 실제 factor 계산 |
| Full production replay | PASS | 4개 complete fixture PASS, insufficient/quality fixture는 COLLECTING |
| Local Test UI | PASS | `scripts/run_integration_ui.py`, HTTP endpoint 확인 |
| 전체 테스트 | PASS | `pytest -q` → 192 passed, 30 warnings |

## 실제 fixture 결과

- `seoul_bus_route.csv`: PASS, 0.9257 km, actual `rail`, expected `walk`
- `seoul_subway_line1.csv`: PASS, 4.6869 km
- `seoul_car_no_transit.csv`: PASS, 1.4147 km
- `seoul_walk_bike.csv`: PASS, 0.1703 km
- `insufficient_gps.csv`: `COLLECTING` (정상적인 입력 부족 상태)
- `quality_edge_cases.csv`: `COLLECTING`, duplicate 1건/out-of-order 1건 거부

## 실행

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant --pipeline
python scripts/run_integration_ui.py
pytest -q
```

상세 JSON 결과는 `reports/integration/validation.json`에 저장됩니다.
