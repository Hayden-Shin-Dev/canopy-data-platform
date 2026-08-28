# GeoLife label pipeline 손실 확인

원본 `labels.txt`와 60초 Window 산출물을 비교해 mode mapping 및 Window 단계의 손실을 확인했습니다.

## 원본 label row

- walk 6,460
- bus 2,853
- bike 2,089
- taxi 1,179
- subway 813
- car 993
- train 299
- airplane 17
- boat 7
- run 6
- motorcycle 2

정의되지 않은 raw mode는 0개입니다. mapping은 `taxi→car`, `subway/train→rail`이며 `airplane/boat/motorcycle/run`은 제외 정책에 따라 학습 target에 넣지 않았습니다.

## Window 단계

- labeled Window: 214,508개
- selected Window: 213,549개
- ambiguous Window: 85개
- unlabeled Window: 1,013,985개
- selected mode: walk 62,969 / bus 51,663 / car 41,961 / bike 30,342 / rail 26,614

rail과 bus가 mapping에서 사라진 증거는 없습니다. 주요 감소 지점은 GPS timestamp가 label interval에 없거나(`unmatched`), interval이 겹쳐 단일 label을 선택할 수 없는 경우(`ambiguous`), 그리고 Window 최소 coverage 기준입니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_label_pipeline `
  "C:\path\to\Geolife Trajectories 1.3.zip" `
  "data/processed/mobility_recognition/geolife_windows_60s.csv" `
  "data/processed/mobility_recognition/geolife_windows_60s.summary.json"
```
