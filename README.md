# KTDB Population Baseline

## 목적

특정 시간, 지역, OD 등의 조건에서 사람들이 일반적으로 어떤 이동수단을 선택하는지 확률을 만드는 데이터 Pipeline입니다.

## Raw Data

KTDB 개인통행실태조사 2021

## 최종 Mode

`walk`, `bike`, `car`, `bus`, `rail`

## 주요 Feature

`weekday`, `departure_hour`, `time_band`, `origin`, `destination`, `od_scope`, `commute_direction`

거리 Feature는 원본에 좌표가 없어 현재 결측으로 유지합니다.

## 처리 과정

Raw → Codebook Mapping → Cleaning → Feature Engineering → Population Dataset → Baseline Lookup → Expected Behaviour Model

## 결과

- Raw trips: 356,899
- Valid features: 331,189
- Commute trips: 86,561
- Train / Validation / Test: 232,489 / 49,396 / 49,304
- Accuracy: 약 0.677
- Macro F1: 약 0.411

## 주요 산출물

- `01_population_model_training_all.csv`
- `02_population_model_training_commute.csv`
- `03_population_lookup_all.csv`
- `04_population_lookup_commute.csv`
- `05_mode_mapping.csv`
- `06_dataset_summary.json`
- Model: `models/expected_behaviour/ktdb_population_baseline.pkl`

## 현재 한계

- 행정동 좌표가 없어 거리 Feature 미완성
- 현재 환경에서는 sklearn fallback 사용
- 원본과 대용량 생성 데이터는 Git에서 제외

## 실행

```powershell
python -m pytest -q
python -m src.build_population_dataset
python -m src.validate_dataset
python -m src.train_expected_behaviour
```
