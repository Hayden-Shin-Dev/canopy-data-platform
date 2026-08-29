# Integration 평가 비교

이 문서는 감사 작업 시작 시 확인한 기준값과 현재 production pipeline의 값을 나란히 기록한다. Test Set은 모델 선택에 사용하지 않았고, Mock Ground Truth는 평가 비교에만 사용했다.

## Before / After

| 지표 | Before | After | 근거 |
| --- | ---: | ---: | --- |
| GeoLife Accuracy | 0.6681 | 0.6942 | `data/processed/mobility_recognition/geolife_final_test_metrics.json`, `reports/hardening/geolife_model_selection_manifest.json` |
| GeoLife Macro F1 | 0.4715 | 0.5330 | 같은 파일 |
| GeoLife Weighted F1 | 0.6676 | 0.6820 | 같은 파일 |
| GeoLife rail F1 | 0.0149 | 0.1701 | 독립 Test classification report |
| GeoLife bus F1 | 0.2087 | 0.6008 | 독립 Test classification report |
| KTDB Accuracy | 0.6771 | 0.6771 | `reports/integration/SYSTEM_AUDIT.md` |
| KTDB Macro F1 | 0.4106 | 0.4106 | `reports/integration/SYSTEM_AUDIT.md` |
| KTDB calibration | 측정 안 함 | 측정 안 함 | 별도 calibration 평가 필요 |
| Mock realtime sequence | `walk → bike → walk` | `walk → bike → rail → walk` | `reports/integration/mock_trip_evaluation.json` |
| Mock final sequence | 단일 최종 mode 표시 | `walk → bike → rail → walk` | `reports/integration/mock_trip_evaluation.json` |
| Actual CO2 | 0.0 g 단일 mode 계산 | 232.4 g | 같은 파일 |
| Expected CO2 | 668.0 g | 668.0 g | 같은 파일 |
| CO2 Reduction | 미계산 | 435.6 g | 같은 파일 |

Before의 GeoLife 값은 기존 120초 모델의 독립 Test 결과다. After는 동일한 사용자 Group Split과 독립 Test를 사용한 품질 필터링 모델 결과다. Transit와 segment의 Before 값은 개선 전 raw GeoLife 출력이며, After 값은 동일 GPS에 production Transit Context와 segment assembly를 적용한 결과다.

## Component별 확인 상태

- GeoLife 5-class: 독립 Test에서 Accuracy, Macro F1, Weighted F1과 class별 Precision/Recall/F1을 기록했다. rail F1은 여전히 낮아 GPS-only 한계로 남겼다.
- Transit Context: 서울 subway reference와 실제 station ID progression을 사용한 integration trace는 PASS다. 전체 실사용 bus/rail Precision·Recall은 labelled replay가 없어 측정하지 않았다.
- Trip segmentation: 모든 GPS edge를 하나의 segment에만 배정하고, segment 거리 합계와 전체 GPS 거리가 일치한다.
- Emission: segment별 거리와 factor를 곱해 Actual CO2를 계산하며, factor 출처와 단위는 `reports/integration/SYSTEM_AUDIT.md`에 기록했다.
- UI: backend의 resolved mode, segment, CO2 값을 표시한다. 이동수단 SVG는 backend mode가 바뀔 때만 갱신되며 line 이름은 rail evidence가 있을 때만 표시한다.

## 남은 측정 항목

Calibration(Brier/reliability), Transit 전체 labelled Precision·Recall, 실제 장시간 iPhone 수집 데이터 검증은 아직 측정하지 않았다. 이 항목들이 채워지기 전에는 Integration을 전면적인 운영 완료로 표현하지 않는다.
