# Canopy 전체 시스템 Audit

검증 기준: `mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv` 433개 이벤트와 기존 독립 Test 산출물. Ground Truth는 비교용으로만 읽었고 inference 입력에는 사용하지 않았다.

## 1. Architecture Audit

| 단계 | 실제 구현 | 결과 |
| --- | --- | --- |
| GPS Event | `src/integration/gps_contract.py` | PASS |
| Ingestion / Replay | `src/integration/replay.py`, `src/integration/ingestion.py` | PASS |
| 120초 Window | `src/integration/geolife_adapter.py` → 기존 `src/geolife/windows.py` | PASS |
| GeoLife Actual Behaviour | 기존 `infer_windows()`와 저장 모델 | PASS |
| Transit Context | `src/integration/pipeline.py` → `src/transit_context/evidence.py` | PASS |
| Final Mode | `src/transit_context/resolver.py`, `src/integration/segments.py` | FIXED |
| Multi-Segment | `run_full_pipeline()`의 시간순 Window 병합 | FIXED |
| GPS Distance | `src/integration/distance.py` | PASS |
| KTDB Baseline | `src/integration/ktdb_context.py` → 기존 KTDB model | FIXED |
| Expected / Actual CO2 | `src/integration/emissions.py`, 기존 factor resolver/calculator | FIXED |
| UI | `scripts/run_integration_ui.py` | FIXED |

Mock CSV의 금지된 label field는 0개이고, 433개 이벤트가 모두 accepted였다. UI는 backend 응답의 값을 표시하며 User Mode에서 Ground Truth, raw JSON, feature 원문을 표시하지 않는다.

## 2. KTDB

실제 입력 feature는 `reports/integration/mock_trip_evaluation.json`의 `ktdb_baseline.features`에 기록했다. 토요일 08시 KST, 출근 목적, 영등포구 → 종로구, SGIS centroid 직선거리 8.0166km, `5-10km`, `same_sido` 조건이다. UTC를 그대로 weekday/hour로 사용하지 않는다.

현재 확률은 walk 5.44%, bike 0.18%, car 20.74%, bus 11.96%, rail 61.69%이며 예측 mode는 rail이다. 정확히 같은 OD 행을 임의로 선택하지 않고, 실제 GPS endpoint에서 feature를 계산해 모델에 전달한다.

독립 Test 결과는 Accuracy 0.6771, Macro F1 0.4106이다. class F1은 walk 0.6856, bike 0.0029, car 0.7578, bus 0.1037, rail 0.5030이다. Confusion Matrix와 support는 모델 재평가 출력에 기록했으며, probability calibration metric은 현재 산출하지 않아 NOT MEASURED로 남긴다. 사용자 group split 중복은 0건이다.

## 3. KTDB Distance

KTDB 코드는 10자리, SGIS 코드는 7자리라 직접 overlap은 0이다. `ktdb_sgis_admin_dong_mapping_2021.csv`의 full admin name mapping을 사용한다. SGIS 좌표는 EPSG:5179에서 WGS84로 변환한 뒤 Haversine을 계산한다. KTDB OD distance는 Population Baseline feature이고, Actual CO2에는 GPS trajectory distance 10.1796km를 사용한다.

## 4. GeoLife

독립 Test Accuracy 0.6942, Macro F1 0.5330, Weighted F1 0.6820이다. class F1은 bike 0.5577, bus 0.6008, car 0.4524, rail 0.1701, walk 0.8841이다. rail recall은 0.1493으로 낮고 car와의 혼동이 366건이다. bus는 recall 0.8149이나 car 117건, walk 173건과 혼동된다. Mock에서 GeoLife 원시 Window sequence는 `walk → bike → walk`로 별도 기록한다.

## 5. Transit Context

서울 subway reference의 `station_id` 2527, 2528, 2529, 2530, 2531, 2532, 2533, 2534가 각 Window의 실제 nearest station으로 관측되며 CSV의 `line` field가 모두 `5`다. resolver는 역 순서가 두 개 이상 확인된 Window부터 rail을 선택하고, 이후 sequence evidence를 누적한다. UI의 노선명은 코드에 `5호선`으로 하드코딩하지 않고 backend `matched_subway_line`에서 가져온다.

Realtime 판정은 해당 시점까지 들어온 Window와 누적 station history만 사용한다. 전체 Trip을 종료한 뒤에만 최종 Segment와 총 emission을 확정한다.

## 6. Bike False Positive

1.63km 구간의 첫 두 Window는 GeoLife가 bike를 예측했고, Transit Context는 각각 station 1개만 관측해 sequence score가 0이었다. 따라서 resolver가 rail을 강제하지 않은 것은 현재 증거 기준으로 정상이다. 세 번째 Window에서 station 2527 → 2528 순서가 확인되어 rail evidence가 생겼고, 최종 Segment는 `walk → bike → rail → walk`가 되었다. 이 결과는 Mock label, 좌표, 특정 노선 규칙으로 보정하지 않았다.

## 7. Trip Segmentation

최종 sequence는 `walk → bike → rail → walk`이다. Segment 거리는 각각 0.634km, 1.638km, 7.515km, 0.393km이며 합계는 10.1796km로 GPS 전체 거리와 일치한다. 경계 GPS edge는 다음 Segment에 한 번만 배정한다.

## 8. Emission

| Segment | 거리 | Factor | Unit | CO2e |
| --- | ---: | ---: | --- | ---: |
| walk | 0.634km | 0.0 | gCO2e/person.km | 0.0g |
| bike | 1.638km | 0.0 | gCO2e/person.km | 0.0g |
| rail | 7.515km | 30.92 | gCO2e/passenger.km | 232.4g |
| walk | 0.393km | 0.0 | gCO2e/person.km | 0.0g |

Actual CO2는 Segment별 `distance × factor` 합계로 232.4g이다. walk/bike 0은 lifecycle 전체가 아닌 현재 operational/direct travel boundary 정책이다.

## 9. Expected CO2

Expected CO2 668.0g은 KTDB probability와 전체 GPS 거리의 factor-weighted sum이다. 기여량은 walk 0.0g, bike 0.0g, car 350.2g, bus 123.6g, rail 194.2g이며 합계 668.0g이다. car는 165.91 gCO2e/vehicle.km, bus는 101.51 gCO2e/passenger.km, rail은 30.92 gCO2e/passenger.km reference row를 사용했다.

## 10. Accuracy Summary

정확도를 100%라고 주장하지 않는다. KTDB와 GeoLife의 독립 Test 수치는 위에 기록한 실제 값이며, Transit는 서울 reference integration test와 433-event E2E evidence 검증으로 평가한다. Segment distance 오차는 0km(구현 후 자동 검증)이고, probability calibration은 아직 측정하지 않았다.

## 11. UI

Home / Active / Result가 상태에 따라 전환되고 지도와 실제 route marker를 표시한다. Active mode는 최신 Window 결과를, Result는 backend의 Segment sequence·거리·CO2를 사용한다. 결과 카드에는 `walk → bike → rail → walk`와 Segment별 배출량이 표시된다. UI 전용 숫자나 mode를 생성하지 않는다.

## 12. Remaining Limitations

- GeoLife GPS-only rail F1은 0.1701로 낮다.
- 첫 두 Window처럼 station sequence가 부족한 구간은 bike 오검출이 남을 수 있다.
- bus/car는 GPS-only로 구조적 혼동이 있어 Transit Context 보강이 필요하다.
- probability calibration과 실기기 iPhone 장시간 replay는 아직 별도 측정이 필요하다.

## 13. Files Changed

세부 변경 파일과 이유는 각 Signed Commit에 남겼다. 핵심 production 변경은 `src/integration/pipeline.py`, `src/integration/segments.py`, `src/transit_context/evidence.py`, `scripts/run_integration_ui.py`이며, 재현용 평가·검증·문서는 `scripts/evaluate_mock_trip.py`, `scripts/render_e2e_report.py`, `scripts/validate_integration_artifacts.py`, `reports/integration/`에 있다.
