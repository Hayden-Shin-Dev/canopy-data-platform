# Canopy Data Platform

## 프로젝트 목적

Canopy는 친환경 이동 자체를 보상하는 것이 아니라, 일반적으로 예상되는 이동행동과 실제 이동행동의 차이를 비교해서 저탄소 방향의 Behaviour Shift가 발생했는지를 측정하는 프로젝트입니다.

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
- Tag: `ktdb-v1.0.0`

GeoLife v1 완료

- 120초 Window 최종 후보
- Test Accuracy: 약 0.668
- Test Macro F1: 약 0.471
- Tag: `geolife-v1.0.0`

Emission Factors: 예정

Transit Context: 필요 여부 검증 예정

Realtime GPS: 예정

Integration: 예정

## Branch

- `main`
- `dev/ktdb-v1`

나머지 dev Branch는 실제 작업을 시작할 때 생성합니다.

## 개발 순서

KTDB → GeoLife → Emission Factors → 필요 시 Transit Context → Realtime GPS → Canopy Integration
