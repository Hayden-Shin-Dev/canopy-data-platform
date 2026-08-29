# KTDB 모델 비교 결과

현재 저장된 `ktdb_population_baseline.pkl`을 같은 person-level train/validation/test split에서 평가하고, 동일 feature contract로 HistGradientBoosting 설정 두 가지를 비교했다. Test는 validation Macro F1이 가장 높은 후보를 고른 뒤 확인했다.

## Before / After

| Metric | 기존 artifact | 선택 모델 | 변화 |
| --- | ---: | ---: | ---: |
| Test Accuracy | 0.6771 | 0.6852 | +0.0081 |
| Test Macro F1 | 0.4106 | 0.4193 | +0.0087 |
| Test Weighted F1 | 0.6430 | 0.6521 | +0.0091 |
| Test Log Loss | 0.8321 | 0.8067 | -0.0254 |
| Test Multiclass Brier | 0.4458 | 0.4340 | -0.0118 |

선택 모델은 `HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=63, learning_rate=0.08)`이다. 기존 artifact의 실제 backend는 CatBoost가 설치되지 않았던 시점에 저장된 sklearn fallback이며, 후보 비교 결과를 반영해 같은 경로에 선택 모델을 저장했다.

## Validation 기준 후보

| 후보 | Validation Accuracy | Validation Macro F1 | Validation Brier |
| --- | ---: | ---: | ---: |
| 기존 artifact | 0.6789 | 0.4140 | 0.4436 |
| HistGradientBoosting leaf31 | 0.6850 | 0.4172 | 0.4342 |
| HistGradientBoosting leaf63 | **0.6894** | **0.4266** | **0.4314** |

## 재현

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_ktdb_model.ps1
```

후보 비교 결과는 `reports/integration/runs/ktdb_candidate_comparison.json`에 저장된다. 이 파일과 모델 artifact는 대용량·생성 파일 정책에 따라 Git에 커밋하지 않으며, 위 명령으로 다시 생성한다.
