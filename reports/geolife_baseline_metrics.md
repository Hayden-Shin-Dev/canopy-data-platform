# GeoLife baseline 학습 결과

60초 Window Dataset에 사용자 기준 train/validation/test split을 적용해 `RandomForestClassifier` baseline을 학습했습니다. 입력 Feature는 GPS Window 수치 Feature만 사용했고 user·trajectory·시간 metadata는 제외했습니다.

## Split

- train: 183,430개 Window, 45명
- validation: 24,759개 Window, 10명
- test: 5,360개 Window, 9명
- random seed: 2021
- estimator: 100

## Metrics

| split | Accuracy | Macro F1 | Weighted F1 |
| --- | ---: | ---: | ---: |
| train | 0.9980 | 0.9978 | 0.9980 |
| validation | 0.6973 | 0.6644 | 0.6926 |
| test | 0.6459 | 0.4566 | 0.6443 |

Test class별 F1은 bike 0.6594, bus 0.2315, car 0.5360, rail 0.0183, walk 0.8376입니다. rail과 bus를 거의 구분하지 못해 사용자 기준 일반화 성능이 충분하지 않습니다.

Confusion matrix의 class 순서는 `bike, bus, car, rail, walk`입니다.

```text
[[ 547,  23, 213,   2,  74],
 [  21,  80, 132,   6,  61],
 [ 112, 179, 715, 327, 174],
 [  12,  29,  22,   6, 232],
 [ 108,  80,  79,  12, 2114]]
```

모델 artifact는 `models/mobility_recognition/geolife_baseline.joblib`에 생성되지만 Git에는 추가하지 않습니다. 학습 metrics JSON도 `data/processed/mobility_recognition/` 아래에서 재생성합니다.

## 재현 명령

```powershell
python -m scripts.train_geolife_baseline `
  "data/processed/mobility_recognition/geolife_windows_60s_split.csv" `
  "models/mobility_recognition/geolife_baseline.joblib" `
  "data/processed/mobility_recognition/geolife_baseline_metrics.json"
```
