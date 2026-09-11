# GeoLife Window Quality Hardening

## 적용 정책

Raw GPS에 공통 품질 정책을 적용했다. 동일 좌표 중복점과 non-positive timestamp 간격은 제거하고, 120초 초과 gap·100 m/s 초과 속도·500 m 초과 고도 jump는 trajectory segment를 나눴다. 정책은 mode와 무관하게 적용된다.

Raw 24,876,977 points 중 24,178,077 points를 사용했다. duplicate 122,483건과 non-positive timestamp 576,417건을 제거했고, long-gap 81,670건·speed 51,584건·altitude 1,030건에서 segment break이 발생했다(총 134,284 segments).

## Window 품질

| Window | 선택 rows | transition | purity < 0.8 | purity < 0.9 | users |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 30s | 389,865 | 1,913 | 1,077 | 1,663 | 64 |
| 60s | 210,318 | 2,190 | 1,219 | 1,681 | 63 |
| 120s | 115,560 | 2,466 | 1,310 | 1,842 | 62 |

최종 120s 모델은 purity >= 0.9 rows 113,718개를 사용했다. 이 데이터에서 `valid_step_count == 0`, `displacement_m > distance_m`, `straightness_ratio > 1`, NaN, inf, 중복 row는 모두 0건이다.

## Split 및 모델

사용자 단위 Group Split을 유지했다. 최종 purity dataset의 train/validation/test rows는 95,346 / 6,647 / 11,725이며, 사용자 중복은 없다. Validation은 Accuracy 0.6969, Macro F1 0.6146이고, 독립 Test는 Accuracy 0.6942, Macro F1 0.5330이다.

Test confusion matrix에서 bus는 1,440/1,767개를 맞췄지만 car 117개와 walk 173개로 혼동됐다. rail은 96/643개로 recall 0.149이며 car 366개로 가장 많이 혼동된다. GPS-only feature만으로 rail·car·bus를 안정적으로 분리하기 어렵다는 근거이며, 향후 Transit Context 보강이 필요하다.

## 재현

`scripts/rebuild_geolife.ps1`가 동일 Raw ZIP에서 30s·60s·120s Window, 사용자 Group Split, purity filtering, 최종 모델과 평가 파일을 순서대로 재생성한다.
