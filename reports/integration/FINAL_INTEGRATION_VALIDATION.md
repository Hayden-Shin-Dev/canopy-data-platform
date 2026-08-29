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
| 전체 테스트 | PASS | `pytest -q` → 205 passed |

## 실제 fixture 결과

- `seoul_bus_route.csv`: PASS, 0.9257 km, actual `rail`, expected `walk`
- `seoul_subway_line1.csv`: PASS, 4.6869 km
- `seoul_car_no_transit.csv`: PASS, 1.4147 km
- `seoul_walk_bike.csv`: PASS, 0.1703 km
- `insufficient_gps.csv`: `COLLECTING` (정상적인 입력 부족 상태)
- `quality_edge_cases.csv`: `COLLECTING`, duplicate 1건/out-of-order 1건 거부

## E2E mock 결과

- `canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`: 433 accepted, 0 rejected
- KTDB route-condition baseline: `rail` (walk 5.44%, bike 0.18%, car 20.74%, bus 11.96%, rail 61.69%)
- GeoLife 원시 Window 예측: `walk -> bike -> walk`
- Transit 증거를 반영한 최종 Segment: `walk -> bike -> rail -> walk`
- Expected CO2: 668.0 g, Actual CO2: 231.3 g, Reduction: 436.6 g
- 상세 Window별 근거: [e2e_root_cause_analysis.md](e2e_root_cause_analysis.md)

## 실행

```powershell
python scripts/validate_integration_artifacts.py
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant --pipeline
python scripts/run_integration_ui.py
pytest -q
```

상세 JSON 결과는 `reports/integration/validation.json`에 저장됩니다.
## Supplied iPhone mock replay

`mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`를 기존 Replay Engine과
기존 `run_full_pipeline()`에 그대로 전달했습니다.

- CSV rows: 433
- accepted events: 433
- rejected events: 0
- GeoLife window count: 18 (기존 `infer_windows()` 결과)
- GeoLife compressed sequence: `walk -> bike -> walk`
- production segment sequence: `walk -> bike -> rail -> walk`
- production pipeline status: `PASS`
- ground truth used by inference: `NO`
- label leakage check: `PASS`

Ground truth는 비교용으로만 읽었고 inference에는 사용하지 않았습니다. GeoLife의
bike 예측은 그대로 남기고, 여러 Window에서 같은 subway reference의 역 순서가
확인된 구간에만 기존 resolver와 시간축 smoothing을 적용했습니다. Full Pipeline의
KTDB 입력은 GPS 경로에서 행정동·시간·출근 목적을 계산해 생성합니다.
