# AI-Hub Experiment A 결과

이 문서는 AI-Hub 실제 GPS만으로 학습한 후보를 기존 GeoLife production과 비교한 기록이다. `evaluation_dataset_v3`는 학습이나 튜닝에 사용하지 않고 마지막 blind 확인에만 사용했다.

## 내부 UID 분리 결과

사용자 ID 기준으로 train/validation/test를 분리했다. Test 사용자는 모델 선택에 사용하지 않았다.

| 후보 | Validation Accuracy | Validation Macro F1 | Test Accuracy | Test Macro F1 |
|---|---:|---:|---:|---:|
| RandomForest 60초, unweighted | 0.6801 | 0.6841 | 0.6633 | 0.6426 |
| RandomForest 60초, sampling-robust | 0.6816 | 0.6854 | 0.6631 | 0.6466 |
| RandomForest 120초 aggregate | 0.7190 | 0.7242 | 0.6965 | 0.6867 |
| ExtraTrees 120초 aggregate | 0.7095 | 0.7184 | 0.6949 | 0.6835 |
| HistGradientBoosting 120초 aggregate | **0.7260** | **0.7314** | **0.7058** | **0.6980** |

120초 후보는 인접한 동일 사용자·동일 class TMC 파일을 시간 순서로 결합했다. 원본 GPS와 label 파일은 수정하지 않았다.

## Frozen v3 blind 결과

기존 v3 production과 Hist 120초 후보를 비교했다. 두 실행 모두 700여정 중 698여정을 평가했고, 짧아서 120초 window가 닫히지 않은 2여정은 `COLLECTING`으로 분리됐다. v3 무결성 hash 2,100건은 모두 PASS였다.

| 지표 | 기존 Production Final | AI-Hub Hist 120 Final | 차이 |
|---|---:|---:|---:|
| Accuracy | 0.5265 | 0.4761 | -0.0504 |
| Macro F1 | 0.3452 | 0.3131 | -0.0321 |
| Weighted F1 | 0.5107 | 0.4950 | -0.0157 |

AI-Hub와 기존 모델을 고정 규칙으로 결합한 탐색 후보는 다음 결과를 냈다.

| 지표 | 기존 Production Final | Ensemble Final | 차이 |
|---|---:|---:|---:|
| Accuracy | 0.5265 | **0.5428** | **+0.0163** |
| Macro F1 | 0.3452 | **0.3645** | **+0.0193** |
| Weighted F1 | 0.5107 | **0.5422** | **+0.0315** |

Ensemble class F1은 walk 0.9254, bike 0.3541, car 0.1205, bus 0.1232, rail 0.2995다. 기존 값 대비 car F1이 0.1527에서 0.1205로 하락했기 때문에 전체 gate는 PASS가 아니다. 따라서 이 후보를 기본 production 모델로 교체하지 않았다.

추가로 class-balanced Hist 120초 후보(Test Accuracy 0.6937, Macro F1 0.6695)와 AI-Hub transit override confidence 0.6 후보(raw Accuracy 0.5366, Macro F1 0.3402)를 확인했다. 둘 다 unweighted Hist와 ensemble보다 낮아 선택하지 않았다.

## 원인 판단

v3 validation report와 frozen hash는 PASS다. 문제는 v3가 이상한 데이터라기보다 입력 계약 차이다. AI-Hub TMC는 약 1초 간격 60포인트(60초)이고, v3는 4~30초 간격의 불규칙 GPS다. AI-Hub 원본에는 rail 좌표 누락도 training 26,848건 중 16,136건이 있어 유효 trajectory가 10,712건으로 줄어든다. 내부 holdout 성능은 높지만 이 차이로 v3 일반화가 보장되지 않았다.

기존 Transit 보정은 GeoLife 분포를 기준으로 동작한다. Hist 후보의 raw bus/rail은 좋아졌지만 기존 보정 단계에서 bus recall이 크게 줄어 최종 성능이 낮아졌다. 따라서 서울 실제 labelled holdout 없이 더 높은 성능을 보장할 수 없으며, AI-Hub 후보를 main에 반영하거나 tag를 만들지 않았다.

## 재현 명령

```powershell
python -m scripts.train_aihub_model data/interim/aihub/aihub_120_agg.csv data/interim/aihub/hist_120_agg.joblib data/interim/aihub/hist_120_agg_metrics.json --model-type hist_gradient_boosting --class-weight none --feature-set all --split-manifest data/interim/aihub/aihub_split_manifest.json --window-seconds 120
python -m scripts.evaluate_dataset_v3 --dataset-root data/evaluation/seoul-synthetic/evaluation_dataset_v3 --run-dir reports/evaluation_v3_aihub_ensemble120 --canopy-baseline-commit d5335dc --evaluation-commit 1f1c09b --mobility-model data/interim/aihub/ensemble_hist120.joblib --window-seconds 120
```
