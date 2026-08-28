# GeoLife Mobility Recognition

## 목적

GeoLife GPS와 transportation label로 Canopy의 실제 이동수단을 Window 단위로 분류하고, 연속 예측을 Multi-modal Trip Segment로 재구성한다.

## Raw Data

Microsoft Research GeoLife Trajectories 1.3

## Target Mode

`walk`, `bike`, `car`, `bus`, `rail`

## 처리 과정

Raw GPS → Label Mapping → GPS Quality Policy → GPS Feature → Window Dataset → Mobility Recognition → Segment Reconstruction

## v1.1.0 hardening 결과

- 최종 Dataset: 120s Window, purity 0.9 이상, 113,718 rows
- 사용자 Group Split: train / validation / test = 95,346 / 6,647 / 11,725 rows
- Validation: Accuracy 0.6969, Macro F1 0.6146
- 독립 Test: Accuracy 0.6942, Macro F1 0.5330
- Test rail F1 0.1701, bus F1 0.6008
- Test 11,725개 Window에서 4,379개 연속 Segment 생성

기존 v1.0.0 Test(Accuracy 0.6681, Macro F1 0.4715) 대비 품질 정책과 label purity filtering을 적용했다. Test는 모델 선택에 사용하지 않고 최종 1회 평가했다.

## 개발 타임라인

Raw parser와 label mapping → Window feature와 사용자 Group Split → 30/60/120s 모델 비교 → GPS quality 정책과 timestamp 정리 → purity filtering → segment schema 확장 → lineage·manifest 검증 → 최종 Test 평가

## 한계

GPS-only Feature만으로 rail·bus·car를 안정적으로 구분하기 어렵다. 최종 Test에서 rail은 car로, car는 bus로 혼동되는 비율이 높아 Transit Context 보강이 필요하다. 원본에는 도로 route distance가 없어 `distance_m`은 GPS point 간 누적거리다.

## 실행

```powershell
./scripts/rebuild_geolife.ps1 -RawZip "C:/path/Geolife Trajectories 1.3.zip"
py -3.13 -m scripts.validate_geolife_lineage "C:/path/Geolife Trajectories 1.3.zip" data/processed/mobility_recognition/geolife_120s_purity_090.csv
```

분석 결과와 lineage는 `reports/geolife_*.md` 및 `reports/geolife_lineage_validation.json`에 기록한다.
