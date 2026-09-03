# AI-Hub raw 120초 runtime parity release

기준 브랜치: `feature/mobility-runtime-parity-v3`

이번 변경은 AI-Hub의 60초 요약 행을 이어 붙여 120초처럼 사용하던 학습 경로를 제거하고, 원본 GPS에서 고정 120초 Window를 만든 뒤 같은 canonical Feature Extractor를 학습과 runtime에 함께 사용하는 작업이다.

## 데이터와 분할

- 입력: AI-Hub `01-1.정식개방데이터` 원본 GPS
- native raw Window: 43,267건
- UID split: Train 729명, Validation 158명, Test 158명
- UID overlap: Train/Validation/Test 모두 0
- Train cadence view: 2초, 5초, 10초 downsample을 Train에만 추가
- Validation/Test cadence view: 학습에 사용하지 않음
- 원본 GPS와 Frozen 평가 데이터는 수정하지 않음

## 모델 선택

Validation Macro F1을 기준으로 후보를 선택했다. 최종 artifact는 `c3_hgb_robust_cadence`이며, 모델 선택 이후 Test를 한 번 평가했다.

| 지표 | Validation | Test |
|---|---:|---:|
| Accuracy | 0.7182 | 0.6749 |
| Macro F1 | 0.7261 | 0.6749 |
| Weighted F1 | 0.7149 | 0.6958 |
| Log loss | 0.7324 | 0.7855 |
| Brier score | 0.3946 | 0.4157 |

Test의 canonical holdout 비교는 `AIHUB_RUNTIME_PARITY_BASELINES.json`에 있으며, 이전 summary 기반 artifact는 참고용으로만 남겼다. 새 production artifact는 raw 120초 계약을 만족하는 `models/mobility_recognition/aihub_canonical_raw120.joblib`이다.

## 단계별 평가

모든 단계는 같은 UID-disjoint Test에서 평가했으며 Ground Truth는 Movement 추론 이후 평가 집계에만 읽었다.

| 단계 | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| Movement | 0.6984 | 0.6770 | 0.6973 |
| Temporal | 0.6984 | 0.6770 | 0.6973 |
| Transit (수정 전) | 0.6527 | 0.5525 | 0.6224 |
| Final (수정 전) | 0.6530 | 0.5538 | 0.6232 |
| Transit (수정 후) | 0.6953 | 0.6665 | 0.6921 |
| Final (수정 후) | 0.7080 | 0.6888 | 0.7066 |

수정 후 Final은 Movement 대비 Macro F1이 0.0117 상승했다. class별 Test F1은 다음과 같다.

| Mode | Movement | Final |
|---|---:|---:|
| walk | 0.8318 | 0.8394 |
| bike | 0.5664 | 0.5651 |
| car | 0.7018 | 0.7061 |
| bus | 0.6234 | 0.6290 |
| rail | 0.6619 | 0.7041 |

상세 confusion matrix와 precision/recall은 `AIHUB_PIPELINE_STAGE_EVALUATION_AFTER.json`을 확인한다.

## Mock replay

`mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`를 실제 Production orchestration에 넣었다.

- 입력 433건, rejected 0건
- Movement: `walk → rail → walk`
- Final: `walk → rail → walk`
- rail 구간의 실제 reference line: 5호선
- Ground Truth 기반 보정: 없음
- Expected CO2: 695.58 g
- Actual CO2: 283.00 g
- CO2 Reduction: 412.57 g

전후 원본은 각각 `AIHUB_RUNTIME_PARITY_MOCK.json`, `AIHUB_RUNTIME_PARITY_MOCK_AFTER.json`이다.

## Sampling cadence

독립 Test에서 native와 downsample view를 비교했다.

| View | Macro F1 | Prediction flip rate |
|---|---:|---:|
| Native | 0.6749 | 0.0000 |
| 2초 | 0.6799 | 0.0759 |
| 5초 | 0.6784 | 0.1164 |
| 10초 | 0.6480 | 0.1629 |

10초 간격은 성능과 예측 변동이 악화되므로 production 선택 기준으로 사용하지 않는다. 상세 결과는 `AIHUB_CADENCE_STRESS.json`이다.

## 변경 원인과 운영

- 학습과 runtime 모두 `src/aihub/features.py::canonical_window_features`를 사용한다.
- production rebuild는 `scripts/build_aihub_duration_windows.py`에서 raw GPS 120초 Window를 만들고 Train cadence만 추가한다.
- `src/integration/model_config.py`는 canonical artifact를 우선 사용하고, 파일이 없을 때 기존 `aihub_hist120.joblib`와 GeoLife artifact 순으로 rollback한다.
- Transit resolver는 구조화된 역 순서가 없더라도 고신뢰 rail 예측을 무조건 bus/car로 덮어쓰지 않는다. 이미 rail이 시작된 경우에는 약한 단일 Window로 mode를 끊지 않는다.
- 모든 inference 경로는 Ground Truth 파일을 읽지 않는다.

## 실행 명령

```powershell
$env:AIHUB_DATA_ROOT = "C:\path\to\01-1.정식개방데이터"
.\scripts\rebuild_aihub_production.ps1
python -m scripts.evaluate_mock_trip --csv mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv --ground-truth mock/canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt --output reports/aihub/AIHUB_RUNTIME_PARITY_MOCK_AFTER.json
```

전체 regression은 저장소 루트에서 `python -m pytest -q`로 실행한다.

