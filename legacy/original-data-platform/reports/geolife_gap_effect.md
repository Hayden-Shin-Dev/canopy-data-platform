# GeoLife sampling gap 영향

전체 raw trajectory에서는 120초 초과 gap이 81,670개 있었지만, selected 60초 Window의 Feature에서 gap이 남았는지 mode별로 확인했습니다.

| mode | Window | gap 포함 Window | gap ratio | valid step median | avg interval median |
| --- | ---: | ---: | ---: | ---: | ---: |
| walk | 62,969 | 0 | 0.0000 | 19 | 2.0714초 |
| bike | 30,342 | 0 | 0.0000 | 29 | 2.0000초 |
| car | 41,961 | 0 | 0.0000 | 11 | 4.4615초 |
| bus | 51,663 | 0 | 0.0000 | 26 | 2.0000초 |
| rail | 26,614 | 0 | 0.0000 | 28 | 2.0000초 |

## 판단

현재 selected Window에는 gap step이 없으므로 rail/bus Test 성능 저하를 긴 sampling gap에 의한 Feature 왜곡으로 설명할 수 없습니다. raw gap은 unlabeled 또는 coverage 기준 미달 Window에 주로 남았고, 120초 gap 제외 규칙은 학습 대상에 적용된 상태입니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_gap_effect `
  "data/processed/mobility_recognition/geolife_windows_60s_split.csv"
```
