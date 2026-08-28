# GeoLife Window 품질 (Hardening 후)

30초·60초·120초 Window를 동일한 Raw ZIP과 `min_points=2`, `label_coverage=0.5` 조건으로 재생성했다. GPS quality 정책은 `max_speed=100m/s`, `max_gap=120s`, `max_altitude_jump=500m`이며 mode label을 사용하지 않는다.

| Window | 전체 선택 | Transition | purity < 0.8 | purity < 0.9 | 사용자 | NaN/inf | 중복 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30초 | 389,865 | 1,913 | 1,077 | 1,663 | 64 | 0 / 0 | 0 |
| 60초 | 210,318 | 2,190 | 1,219 | 1,681 | 63 | 0 / 0 | 0 |
| 120초 | 115,560 | 2,466 | 1,310 | 1,842 | 62 | 0 / 0 | 0 |

세 Dataset 모두 `valid_step_count == 0`, `displacement_m > distance_m`, `straightness_ratio > 1` Window가 0개였다. 품질 정책 적용 중 원본 24,876,977 point에서 동일하게 122,483 duplicate point를 제거하고, non-positive timestamp 576,417개를 drop했다. 120초 기준 split은 train 96,652 / validation 6,791 / test 12,117 Window이며 사용자 겹침은 없다.

purity threshold는 데이터셋에 값을 기록하는 용도로만 적용했고, v1 최종 filtering 진리로 고정하지 않았다. 0.8·0.9 비교 Dataset은 `scripts/filter_geolife_windows.py`로 재현한다.
