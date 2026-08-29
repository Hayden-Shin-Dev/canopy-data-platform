# Canopy Data Platform

## 프로젝트 목적

Canopy는 친환경 이동 자체를 보상하는 것이 아니라, 일반적으로 예상되는 이동행동과 실제 이동행동의 차이를 비교해서 저탄소 방향의 Behaviour Shift가 발생했는지를 측정하고 탄소배출량과 리워드를 제공하는 서비스

## 전체 구조

KTDB — Expected Behaviour / Population Baseline

GeoLife — Mobility Recognition Model 학습

Emission Factors — 교통수단별 CO2 환산 기준

Transit Context — GPS만으로 구분이 어려운 bus/car 등의 판단 보조

Realtime GPS — iOS에서 실제 사용자 GPS 수집 및 Streaming

Integration — Expected Behaviour와 Actual Behaviour를 비교하고 CO2 Reduction 및 Reward 계산

## 현재 진행 상태

KTDB v1 완료

- Raw trips: 356,899
- Valid features: 331,189
- Commute trips: 86,561
- Test Accuracy: 약 0.677
- Macro F1: 약 0.411
- Tag: `ktdb-v1.0.0`, `ktdb-v1.1.0`

GeoLife v1 완료

- 120초 Window + GPS quality + purity filtering
- Test Accuracy: 0.6942
- Test Macro F1: 0.5330
- Tag: `geolife-v1.0.0`, `geolife-v1.1.0`

Emission Factors v1 완료

- GOV.UK 2026 source audit 및 5개 canonical mode reference
- Tag: `emission-factors-v1.0.0`

Transit Context: 필요 여부 검증 예정

Realtime GPS: 예정

Integration: 예정

## Branch

- `main`
- `dev/ktdb-v1`
- `dev/geolife-v1`
- `dev/emission-factors-v1`

나머지 dev Branch는 실제 작업을 시작할 때 생성합니다.

## 개발 순서

KTDB → GeoLife → Emission Factors → 필요 시 Transit Context → Realtime GPS → Canopy Integration

## KTDB SGIS 거리 Feature

KTDB의 10자리 행정동 코드를 SGIS 2021 읍면동(7자리) reference와 전체 행정구역명으로 매칭합니다. SGIS가 제공한 EPSG:5179 대표좌표를 WGS84로 변환한 뒤 Haversine 직선거리를 계산하며, Polygon을 평균내지 않습니다.

SGIS 키는 환경변수로만 전달합니다.

```powershell
$env:SGIS_CONSUMER_KEY = "발급받은 키"
$env:SGIS_CONSUMER_SECRET = "발급받은 시크릿"
py -3.13 -m src.build_population_dataset
```

기존 `data/reference/admin_dong_centroids_2021.csv`가 있으면 재사용하고, 다시 수집할 때는 `--refresh-sgis`를 붙입니다. API 원본 응답은 `data/reference/sgis/raw/2021/`에 로컬 cache로 저장되며 Git에는 올리지 않습니다.
