# GeoLife mode별 split coverage

60초 Window Dataset의 `user_id`와 `canonical_mode`를 기준으로 집계했습니다. 같은 user는 한 split에만 존재합니다.

| mode | Train users / windows | Validation users / windows | Test users / windows |
| --- | ---: | ---: | ---: |
| walk | 42 / 52,356 | 9 / 8,220 | 9 / 2,393 |
| bike | 22 / 21,971 | 6 / 7,512 | 3 / 859 |
| car | 29 / 38,038 | 9 / 2,416 | 7 / 1,507 |
| bus | 31 / 47,605 | 7 / 3,758 | 5 / 300 |
| rail | 20 / 23,460 | 7 / 2,853 | 2 / 301 |

## 확인 사항

- Train에는 5개 mode가 모두 충분히 존재합니다.
- Test rail은 2명·301 Window로 사용자 다양성이 가장 낮습니다.
- Test bus는 5명·300 Window로 Window 수도 적습니다.
- 따라서 rail/bus의 낮은 Test F1은 class 자체의 GPS 구분 난이도와 함께 사용자 holdout 표본 부족 영향을 받을 수 있습니다.
- 이 결과만으로 split을 바꾸지 않고, Validation 기준 개선 비교를 먼저 수행합니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_mode_users `
  "data/processed/mobility_recognition/geolife_windows_60s_split.csv"
```
