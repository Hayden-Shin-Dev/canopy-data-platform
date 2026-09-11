# GeoLife mode별 Feature 분포

학습 대상 60초 Window 213,549개를 mode별로 집계했습니다. 아래 값은 각 Feature의 median입니다.

| mode | mean speed | max speed | speed std | mean abs accel | stop ratio | distance m | displacement m | straightness | heading change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| walk | 1.2592 | 2.4586 | 0.5359 | 0.1788 | 0.0833 | 61.96 | 45.66 | 0.8181 | 29.96 |
| bike | 3.2316 | 5.4034 | 0.8750 | 0.2852 | 0.0000 | 171.30 | 151.31 | 0.9410 | 14.82 |
| bus | 4.8489 | 10.0280 | 2.3105 | 0.3487 | 0.0556 | 238.26 | 217.88 | 0.9616 | 17.61 |
| car | 8.2913 | 13.3373 | 1.7960 | 0.2729 | 0.0000 | 423.60 | 386.36 | 0.9929 | 5.75 |
| rail | 18.0066 | 20.5177 | 0.7570 | 0.2795 | 0.0000 | 967.12 | 948.23 | 0.9950 | 2.04 |

## rail / bus 해석

- rail은 속도·거리·직진성이 bus보다 높아 일부 구분 신호가 있습니다.
- rail의 speed std와 acceleration은 bus와 겹치며, 저속·정차 구간은 walk로도 보일 수 있습니다.
- bus는 car와 mean speed, distance, straightness 구간이 겹칩니다. bus median speed는 car보다 낮지만 p75 범위가 넓어 GPS-only 완전 분리는 어렵습니다.
- walk와 bus도 stop ratio와 heading change가 겹치는 구간이 있어 정류장·환승 context가 없으면 혼동이 남습니다.

전체 mode·Feature의 p25/median/p75 값은 분석 스크립트 출력에서 재생성할 수 있습니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_feature_distribution `
  "data/processed/mobility_recognition/geolife_windows_60s_split.csv"
```
