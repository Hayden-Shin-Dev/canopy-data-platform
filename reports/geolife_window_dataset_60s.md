# GeoLife 60초 Window Dataset

`Geolife Trajectories 1.3.zip`을 원본으로 60초 후보 Window를 생성했습니다. 생성 CSV와 summary JSON은 Git에 커밋하지 않고 코드로 재생성합니다.

## 생성 결과

- 후보 Window: 1,228,578개
- labeled Window: 214,508개
- 학습 대상 Window: 213,549개
- 기준: 최소 2 point, label coverage 0.5 이상, 유일한 majority canonical mode
- ambiguous Window: 85개
- unlabeled Window: 1,013,985개
- parser 오류: 1개

학습 대상 mode별 Window:

- walk: 62,969
- bus: 51,663
- car: 41,961
- bike: 30,342
- rail: 26,614

## 재현 명령

```powershell
python -m scripts.build_geolife_windows `
  "C:\path\to\Geolife Trajectories 1.3.zip" `
  "data/processed/mobility_recognition/geolife_windows_60s.csv" `
  --window-seconds 60 `
  --min-label-coverage 0.5
```
