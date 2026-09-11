# GeoLife 모델 비교 결과

같은 `geolife_120s_purity_090.csv`와 기존 user 단위 train/validation/test split을 사용해 후보 모델을 비교했다. Test는 validation Macro F1로 모델을 고른 뒤 한 번만 확인했다. Ground Truth는 학습 입력에 포함하지 않았다.

## 후보 비교

| 모델 | Feature set | Validation Accuracy | Validation Macro F1 | Test Accuracy | Test Macro F1 | Test Weighted F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| RandomForest | base | 0.6954 | 0.6133 | 0.6942 | 0.5330 | 0.6820 |
| ExtraTrees | base | 0.6785 | 0.5951 | 0.6815 | 0.5187 | 0.6664 |
| HistGradientBoosting | base | 0.7006 | 0.6116 | 0.7110 | 0.5516 | 0.6989 |
| CatBoost | base | **0.7057** | **0.6163** | **0.7183** | **0.5616** | **0.7056** |
| RandomForest | derived | 0.6991 | 0.6154 | 0.6978 | 0.5336 | 0.6845 |
| ExtraTrees | derived | 0.6874 | 0.6025 | 0.6878 | 0.5235 | 0.6722 |
| HistGradientBoosting | derived | 0.7036 | 0.6163 | 0.7093 | 0.5537 | 0.6972 |
| CatBoost | derived | 0.7020 | 0.6123 | 0.7150 | 0.5549 | 0.7014 |

`base`는 현재 16개 Window Feature이고, `derived`는 속도·가속도·유효 샘플 비율에서 계산한 파생값을 추가한 구성이다. Validation Macro F1이 가장 높은 CatBoost base를 production 재현 명령의 모델로 선택했다.

## 선택 모델의 Test 상세

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| walk | 0.8718 | 0.9221 | 0.8963 | 5,856 |
| bike | 0.6374 | 0.4931 | 0.5560 | 795 |
| car | 0.6810 | 0.3990 | 0.5032 | 2,664 |
| bus | 0.4984 | 0.8127 | 0.6179 | 1,767 |
| rail | 0.2764 | 0.2037 | 0.2346 | 643 |

Test Accuracy는 0.7183, Macro F1은 0.5616이다. 기존 production RandomForest 결과(Accuracy 0.6942, Macro F1 0.5330)보다 전체 지표가 개선됐다. car는 Recall 0.3990으로 별도 한계가 남아 있어 Transit Context와 함께 검증해야 한다.

## Confusion Matrix

행은 실제 Class, 열은 예측 Class이며 순서는 `bike, bus, car, rail, walk`이다.

```text
[[392, 167,   8,   2, 226],
 [ 29, 1436, 104,  19, 179],
 [ 87, 967, 1063, 294, 253],
 [  3,  40, 333, 131, 136],
 [104, 271,  53,  28, 5400]]
```

rail은 car로 혼동되는 비율이 가장 크고, car는 bus와 rail로도 자주 분산된다. 이 패턴은 GPS-only 분류만으로는 한계가 있다는 근거이며, 특정 노선 규칙으로 보정하지 않고 실제 Transit evidence를 별도로 사용한다.

## 재현

```powershell
python -m scripts.experiment_geolife_candidates `
  data/processed/mobility_recognition/geolife_120s_purity_090.csv `
  reports/integration/runs/geolife_candidate_comparison.json

python -m scripts.train_geolife_baseline `
  data/processed/mobility_recognition/geolife_120s_purity_090.csv `
  models/mobility_recognition/geolife_hardened_120s_purity_090.joblib `
  data/processed/mobility_recognition/geolife_hardened_120s_purity_090_metrics.json `
  --model-type catboost --class-weight none --n-estimators 250 --random-seed 2021
```
