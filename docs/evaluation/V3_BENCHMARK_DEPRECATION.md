# evaluation_dataset_v3 사용 정책

`data/evaluation/seoul-synthetic/evaluation_dataset_v3/`는 Production 모델을 고르거나 튜닝하기 위한 데이터가 아닙니다.

## 결정

- 상태: **DEPRECATED FOR PRODUCTION MODEL SELECTION**
- 학습, feature 선택, window 선택, threshold 조정, Release Gate에서 사용하지 않습니다.
- 파일과 기존 평가 보고서는 재현성과 감사 증거를 위해 그대로 보존합니다.
- v3 결과는 과거 synthetic route/geometry benchmark 결과로만 읽습니다.

## 사유

v3는 실제 수집된 서울 GPS holdout이 아닙니다. 생성된 경로와 라벨의 geometry·sampling 특성이 AI-Hub 실제 GPS와 다르기 때문에, v3 성능이 실제 한국 이동수단 판별 성능을 대표한다고 볼 수 없습니다. 특히 route를 단순 보간한 synthetic trajectory는 rail·bus의 공간 패턴과 GPS 품질을 실제 운행과 동일하게 보장하지 않습니다.

따라서 v3에서 AI-Hub 모델이 낮은 점수를 얻었다는 이유로 AI-Hub 모델을 폐기하거나, v3에 맞춰 production 로직을 조정하지 않습니다. v3 원본 무결성 검사는 historical reproducibility 용도로만 유지합니다.

## 현재 평가 기준

AI-Hub 실제 한국 GPS를 primary benchmark로 사용합니다. 사용자를 기준으로 분리한 train/validation/test split을 유지하며, champion 선택은 validation 결과로만 결정합니다. Test 결과는 champion을 고정한 뒤 최종 확인에 사용합니다.

현재 후보인 120초 aggregate HistGradientBoosting의 내부 UID-disjoint 결과는 validation Accuracy 0.7235 / Macro F1 0.7276, test Accuracy 0.7027 / Macro F1 0.6914입니다. 이 수치는 `reports/aihub/AIHUB_EXPERIMENT_A_RESULTS.md`와 재현 스크립트에 기록되어 있습니다.

## Production correctness

v3는 production correctness 확인에 사용할 수 없습니다. Production 입력 계약, GPS 품질 처리, runtime feature parity, replay, transit·emission 회귀 검사는 별도 fixture와 AI-Hub split으로 수행합니다.
