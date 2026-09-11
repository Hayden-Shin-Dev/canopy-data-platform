# KTDB 데이터 흐름

KTDB 원본은 `data/raw/ktdb/`에 보관하고 어떤 단계에서도 수정하지 않는다.

```text
raw CSV/XLSX
  -> loader (encoding·필수 컬럼 확인)
  -> transform (Code Book 기준 feature와 5-class target)
  -> data/processed/population_baseline/ktdb/
       01_population_model_training_all.csv
       02_population_model_training_commute.csv
       03_population_lookup_all.csv
       04_population_lookup_commute.csv
       05_mode_mapping.csv
       06_dataset_summary.json
  -> train_expected_behaviour
  -> predict_expected_behaviour
```

사람 단위 `person_group_id`를 기준으로 split을 고정해 같은 사람의 이동이
train과 평가 집합에 동시에 들어가지 않도록 한다. 대표좌표 원본이 추가되기
전까지 OD 직선거리와 distance band는 결측으로 유지한다.
