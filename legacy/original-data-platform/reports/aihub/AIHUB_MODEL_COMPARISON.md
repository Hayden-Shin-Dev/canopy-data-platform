# AI-Hub Movement ML 후보 비교

이 보고서는 `feature/aihub-mobility-v2`에서 AI-Hub trajectory feature를 사용자 단위로 분리한 뒤 실행한 후보 비교 결과다. 공식 Training/Validation split은 UID가 겹치므로 사용하지 않았고, 두 split의 유효 trajectory를 합친 뒤 UID 70/15/15로 새로 나눴다.

이번 비교는 AI-Hub feature table과 동일한 split에서만 수행했다. `evaluation_dataset_v3`는 사용하지 않았으며, 이 결과만으로 기존 Production model을 교체하지 않는다.

## 데이터와 split

- 유효 trajectory: 84,935개
- 사용자: 1,060명
- Train / Validation / Test 사용자: 742 / 159 / 159
- Train / Validation / Test 행: 59,176 / 11,457 / 14,302
- 사용자 split 중복: 0명
- class: walk, bike, car, bus, rail
- feature version: `aihub-window-v1`

## 후보별 결과

모델 선택은 Validation Macro F1만 사용했다. Test 수치는 선택 후 한 번 확인한 값이다.

| 모델 | Validation Accuracy | Validation Macro F1 | Test Accuracy | Test Macro F1 |
|---|---:|---:|---:|---:|
| ExtraTrees (200) | 0.6638 | 0.6654 | 0.6508 | 0.6280 |
| RandomForest (200) | **0.6789** | **0.6825** | **0.6640** | **0.6444** |
| HistGradientBoosting | 0.6730 | 0.6628 | 0.6491 | 0.6181 |
| CatBoost (400 iterations) | 0.6732 | 0.6613 | 0.6475 | 0.6137 |
| RandomForest, no class weight | **0.6801** | **0.6841** | 0.6633 | 0.6426 |
| RandomForest, base 16 features only | 0.6527 | 0.6606 | 0.6427 | 0.6205 |

현재 Validation 기준 후보는 class weight를 사용하지 않은 RandomForest다(Macro F1 0.6841). Accuracy는 0.6801로 balanced RandomForest보다 높았고, base 16개 feature만 사용한 후보보다도 높았다. 품질 feature 5개가 실제 validation 개선에 기여했다. Test에서도 unweighted RandomForest가 가장 높았지만, Test를 보고 모델을 고른 것은 아니다.

## RandomForest class별 F1

| Mode | Validation F1 | Test F1 |
|---|---:|---:|
| walk | 0.7876 | 0.8033 |
| bike | 0.7157 | 0.5842 |
| car | 0.7220 | 0.6932 |
| bus | 0.5065 | 0.5323 |
| rail | 0.6809 | 0.6092 |

bus와 car가 가장 크게 혼동된다. Test confusion matrix의 실제 행/예측 열 순서는 `walk, bike, car, bus, rail`이다.

```text
[[2412, 26, 182, 161, 111],
 [  53,196,  89,  26,   5],
 [ 217, 48,3973, 741, 239],
 [ 193, 27,1714,1881, 230],
 [ 238,  5, 287, 213,1035]]
```

## 품질상 제한

AI-Hub 원천 GPS 95,948개 중 75,532개만 유효 feature로 생성됐다. SUBWAY는 26,848개 중 10,712개만 사용됐고 16,136개가 유효 GPS point 부족으로 제외됐다. Validation도 SUBWAY 3,356개 중 1,375개만 사용됐다.

따라서 이 모델은 현재 GPS가 실제로 존재하는 trajectory에 대한 후보이며, 지하 구간에서 좌표가 거의 없는 SUBWAY를 자동으로 복원하는 모델이 아니다. 결측 구간을 보간해 새 GPS를 만들지 않았고, Transit Context나 OD Label로 예측을 보정하지 않았다.

## 다음 결정

RandomForest 후보를 Production에 바로 연결하지 않는다. 먼저 공식 codebook을 확인하고, 전체 quality profile과 iPhone 입력 계약을 검증한 뒤, AI-Hub only와 기존 GeoLife 후보를 같은 독립 한국 holdout에서 비교해야 한다. 그 검증과 Production regression을 통과하기 전에는 `main` merge나 release tag를 만들지 않는다.
