# AI-Hub 이동수단 모델 v2

이 브랜치는 AI-Hub 한국 GPS 데이터를 기존 GeoLife 모델과 분리해 검증하는 작업 공간입니다. 원본은 저장소 밖에 두고, 실행할 때 원본에서 feature와 모델을 다시 만듭니다.

## 데이터 위치와 규칙

기본 원본 위치는 다음과 같습니다.

```text
C:\Users\user\Downloads\186.교통수단판별 데이터\01-1.정식개방데이터
```

WALK, BIKE, CAR, BUS, SUBWAY를 각각 `walk`, `bike`, `car`, `bus`, `rail`로 매핑합니다. SUBWAY를 RAIL로 바꾸는 규칙은 `src/aihub/config.py`에만 정의되어 있습니다. GPS와 label 파일의 timestamp가 맞지 않는 파일은 ingestion 단계에서 거부합니다.

공식 Training/Validation UID가 겹치므로 그대로 사용하지 않습니다. 두 split의 유효 trajectory를 합친 뒤 `user_id` 단위로 70/15/15를 나누며, 동일 사용자는 한 split에만 들어갑니다. `evaluation_dataset_v3`와 과거 `dataset_v1`은 학습과 튜닝에 사용하지 않습니다.

## 재생성 순서

PowerShell에서 저장소 루트로 이동한 뒤 실행합니다.

```powershell
$aihub = "C:\Users\user\Downloads\186.교통수단판별 데이터\01-1.정식개방데이터"
python -m scripts.profile_aihub $aihub data/interim/aihub/aihub_training_profile.json --split Training --workers 8 --skip-label-content
python -m scripts.profile_aihub $aihub data/interim/aihub/aihub_validation_profile.json --split Validation --workers 8 --skip-label-content
python -m scripts.build_aihub_windows $aihub data/interim/aihub/aihub_training_windows.csv --split Training --workers 8 --skip-label-content
python -m scripts.build_aihub_windows $aihub data/interim/aihub/aihub_validation_windows.csv --split Validation --workers 8 --skip-label-content
python -m scripts.merge_aihub_windows data/interim/aihub/aihub_training_windows.csv data/interim/aihub/aihub_validation_windows.csv data/interim/aihub/aihub_pool_windows.csv
python -m scripts.assign_aihub_splits data/interim/aihub/aihub_pool_windows.csv data/interim/aihub/aihub_split_windows.csv data/interim/aihub/aihub_split_manifest.json
python -m scripts.train_aihub_model data/interim/aihub/aihub_split_windows.csv data/interim/aihub/rf_unweighted.joblib data/interim/aihub/rf_unweighted_metrics.json --model-type random_forest --n-estimators 200 --class-weight none --split-manifest data/interim/aihub/aihub_split_manifest.json
python -m scripts.validate_aihub_release data/interim/aihub/aihub_split_windows.csv data/interim/aihub/aihub_split_manifest.json data/interim/aihub/rf_unweighted.joblib
```

후보 비교는 같은 `split_windows.csv`에 대해 다음처럼 실행합니다.

```powershell
python -m scripts.compare_aihub_models data/interim/aihub/aihub_split_windows.csv data/interim/aihub/candidates --split-manifest data/interim/aihub/aihub_split_manifest.json
```

모델 artifact에는 feature 순서, class 순서, 60초 window 계약, dataset SHA-256, split manifest SHA-256이 함께 저장됩니다. `src/aihub/runtime.py`는 45초 미만 입력을 `COLLECTING`으로 반환하고, 계약이 다른 artifact는 거부합니다.

## 현재 검증 결과

현재 validation 기준 선택 후보는 class weight를 사용하지 않은 RandomForest입니다. Test는 후보를 고른 뒤 한 번 확인한 값입니다.

| 항목 | Validation | Test |
|---|---:|---:|
| Accuracy | 0.6801 | 0.6633 |
| Macro F1 | 0.6841 | 0.6426 |
| Weighted F1 | 0.6742 | 0.6564 |
| Brier score | 0.4329 | 0.4563 |

Test F1은 walk 0.8011, bike 0.5759, car 0.6919, bus 0.5357, rail 0.6085입니다. car와 bus가 가장 많이 섞이며, rail도 GPS가 실제로 존재하는 trajectory만 반영합니다. Training rail 26,848개 중 유효 window는 10,712개, Validation rail 3,356개 중 1,375개였으므로 rail 결측 원인을 별도 데이터 확보 과제로 남깁니다.

## Production 반영 기준

이 결과만으로 기존 GeoLife production 모델을 교체하지 않습니다. 별도의 독립적인 한국 holdout에서 GeoLife와 AI-Hub 후보를 같은 feature/window 계약으로 비교하고, 기존 integration 회귀와 frozen 평가를 통과한 뒤에만 production 반영을 검토합니다. 현재 AI-Hub artifact는 opt-in runtime 검증용이며 기본 pipeline은 변경하지 않았습니다.
