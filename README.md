# GeoLife Mobility Recognition

## 목적

GeoLife GPS와 transportation label을 이용해 Canopy의 실제 이동수단을 Window 단위로 분류하고, 연속 예측을 Multi-modal Trip Segment로 재구성합니다.

## Raw Data

Microsoft Research GeoLife Trajectories 1.3

## Target Mode

`walk`, `bike`, `car`, `bus`, `rail`

## 처리 과정

Raw GPS
→ Label Mapping
→ GPS Feature
→ Window Dataset
→ Mobility Recognition
→ Segment Reconstruction

## 현재 결과

- 60초 Window: 213,549개
- 최종 후보: 120초 Window + 무가중치 RandomForest
- Validation Accuracy / Macro F1: 0.7203 / 0.6898
- 최종 Test Accuracy / Macro F1: 0.6681 / 0.4715
- Test rail F1: 0.0149, bus F1: 0.2087

## 현재 한계

- GPS-only Feature에서 rail은 주로 walk로, bus는 car로 혼동됩니다.
- car·bus·rail 구분에는 Transit Context 보강이 필요할 수 있습니다.
- 원본 ZIP과 생성 CSV, Model artifact는 Git에서 제외합니다.

## 실행

```powershell
./scripts/rebuild_geolife.ps1 -RawZip "C:/path/Geolife Trajectories 1.3.zip"
```

주요 분석과 평가 결과는 `reports/geolife_*.md`에 기록되어 있습니다.
