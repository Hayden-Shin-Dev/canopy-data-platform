# GeoLife class weight 비교

동일한 60초 Window, 사용자 split, RandomForest 100개 estimator로 class weight만 바꿔 비교했습니다.

| class weight | Validation Accuracy | Validation Macro F1 | Validation Weighted F1 |
| --- | ---: | ---: | ---: |
| `balanced_subsample` | 0.6973 | 0.6644 | 0.6926 |
| `None` | 0.7008 | 0.6671 | 0.6965 |

Validation Macro F1과 Accuracy 모두 `None` 설정이 소폭 높았습니다. 따라서 다음 모델 비교의 기준은 `class_weight=None`으로 정합니다. Test 결과는 이 선택에 사용하지 않았습니다.

두 설정 모두 rail F1이 낮아 class weight만으로 rail 문제를 해결하지 못했습니다. 이후 모델·Window 후보를 Validation 기준으로 비교합니다.

## 재현 명령

```powershell
python -m scripts.train_geolife_baseline `
  "data/processed/mobility_recognition/geolife_windows_60s_split.csv" `
  "models/mobility_recognition/geolife_baseline_unweighted.joblib" `
  "data/processed/mobility_recognition/geolife_baseline_unweighted_metrics.json" `
  --class-weight none
```
