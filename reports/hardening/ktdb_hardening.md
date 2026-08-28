# KTDB Population Baseline Hardening

## 재현 결과

KTDB 원본 356,899 trips 중 331,189개를 유효 feature로 변환했고, 86,561개가 commute subset이다. mode는 walk 98,467, car 172,593, rail 22,382, bus 33,068, bike 4,679이다.

사용자 group 기준 split은 train 232,489 / validation 49,396 / test 49,304이며, `person_group_id` 중복은 없다. lookup은 all/commute 각각 동일 pipeline에서 생성되며 최소 표본수 100 설정을 기록했다.

## 거리 feature 판단

현재 원본에는 신뢰 가능한 행정동 대표 좌표가 없어 `od_straight_distance_km`과 `distance_band`를 모두 결측으로 유지했다. 좌표를 추정하거나 임의 생성하지 않았고, centroid source가 확인될 때만 `src/ktdb/distance.py`를 통해 Haversine 계산을 활성화한다.

## 품질 및 모델

trip_id 중복과 inf는 0건이며, 지원하지 않는 mode도 0건이다. NaN은 행정구역 코드 및 거리 feature의 원본 결측을 포함하므로 수동 보정하지 않는다. 기존 baseline Test 성능(Accuracy 약 0.677, Macro F1 약 0.411)은 변경하지 않고 유지한다.

상세 수치는 `reports/hardening/ktdb_hardening_manifest.json`과 `data/processed/population_baseline/ktdb/06_dataset_summary.json`에 기록한다.
