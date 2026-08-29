# Integration E2E 원인 분석

동일한 433개 iPhone 형식 GPS CSV를 재생해 production pipeline 결과를 기록한 보고서입니다. Ground Truth는 비교에만 사용했고 inference 입력으로 읽지 않았습니다.

## KTDB Baseline

이전에는 processed dataset 첫 행(동일 동네, 거리 0km, 17시 non_commute)을 고정 입력으로 사용해 walk 86.8%, rail 9.4%가 나왔습니다. 이는 UI가 실제 경로 조건을 전달하지 않은 입력 문제였습니다.

현재는 SGIS centroid와 KTDB mapping으로 실제 경로 조건을 만들었습니다. {'weekday': 'Sat', 'departure_hour': 8, 'departure_minute_bin': 0, 'time_band': 'morning_peak', 'origin_admin_dong': '1156053500', 'origin_x': 947659.0, 'origin_y': 1947092.0, 'origin_sido': '서울특별시', 'origin_sigungu': '영등포구', 'destination_admin_dong': '1111053000', 'destination_x': 953230.0, 'destination_y': 1952854.0, 'destination_sido': '서울특별시', 'destination_sigungu': '종로구', 'od_scope': 'same_sido', 'od_straight_distance_km': 8.016554952240018, 'distance_band': '5-10km', 'purpose': '출근', 'commute_direction': 'to_work'}

현재 확률:

- walk: 5.44%
- bike: 0.18%
- car: 20.74%
- bus: 11.96%
- rail: 61.69%

예측 mode: rail
provenance: {'origin_sgis_adm_cd': '1119074', 'destination_sgis_adm_cd': '1101053', 'origin_ktdb_admin_code': '1156053500', 'destination_ktdb_admin_code': '1111053000', 'origin_centroid_distance_source': 'EPSG:5179', 'destination_centroid_distance_source': 'EPSG:5179', 'route_distance_km': 10.179588320609643, 'purpose_source': 'KTDB rows with commute_direction=to_work'}

## Window별 결과

| Window 시작 | GeoLife | 최종 mode | Subway score | Sequence | 관측 station |
| --- | --- | --- | ---: | ---: | --- |
| 2026-08-28T23:00:00+00:00 | walk | walk | 0.000 | 0.000 |  |
| 2026-08-28T23:02:00+00:00 | walk | walk | 0.000 | 0.000 |  |
| 2026-08-28T23:04:00+00:00 | walk | walk | 0.000 | 0.000 |  |
| 2026-08-28T23:06:00+00:00 | walk | walk | 0.000 | 0.000 |  |
| 2026-08-28T23:08:00+00:00 | bike | bike | 0.452 | 0.000 | 2527 |
| 2026-08-28T23:10:00+00:00 | bike | bike | 0.480 | 0.000 | 2527 |
| 2026-08-28T23:12:00+00:00 | bike | rail | 0.663 | 0.500 | 2527,2528 |
| 2026-08-28T23:14:00+00:00 | bike | rail | 0.694 | 0.500 | 2528 |
| 2026-08-28T23:16:00+00:00 | bike | rail | 0.526 | 1.000 | 2529 |
| 2026-08-28T23:18:00+00:00 | bike | rail | 0.795 | 1.000 | 2529,2530 |
| 2026-08-28T23:20:00+00:00 | bike | rail | 0.776 | 1.000 | 2530 |
| 2026-08-28T23:22:00+00:00 | bike | rail | 0.792 | 1.000 | 2531 |
| 2026-08-28T23:24:00+00:00 | bike | rail | 0.793 | 1.000 | 2531,2532 |
| 2026-08-28T23:26:00+00:00 | bike | rail | 0.793 | 1.000 | 2533 |
| 2026-08-28T23:28:00+00:00 | bike | rail | 0.745 | 1.000 | 2533,2534 |
| 2026-08-28T23:30:00+00:00 | walk | walk | 0.720 | 1.000 | 2534 |
| 2026-08-28T23:32:00+00:00 | walk | walk | 0.633 | 1.000 | 2534 |
| 2026-08-28T23:34:00+00:00 | walk | walk | 0.550 | 1.000 | 2534 |

GeoLife 모델은 rail 구간에서 bike를 예측했지만, 여러 Window에 걸쳐 같은 subway reference의 station 순서가 확인된 뒤 resolver가 rail로 보정했습니다. 마지막 고신뢰 walk Window에서는 rail을 종료했습니다. 이는 특정 노선이나 Ground Truth를 사용한 규칙이 아닙니다.

## Trip Segmentation 및 Emission

mode sequence: `walk → bike → rail → walk`

| Segment | Window | 거리(km) | CO2e(g) | Subway line |
| --- | --- | ---: | ---: | --- |
| 1. walk | 0,1,2,3 | 0.634 | 0.0 | - |
| 2. bike | 4,5 | 1.638 | 0.0 | - |
| 3. rail | 6,7,8,9,10,11,12,13,14 | 7.515 | 232.4 | 5 |
| 4. walk | 15,16,17 | 0.393 | 0.0 | - |

- 총 거리: 10.180 km
- Expected CO2: 668.0 g
- Actual CO2: 232.4 g
- Reduction: 435.6 g

Actual CO2는 각 Segment의 거리와 기존 Emission Factor를 곱해 합산했습니다. 마지막 Window 하나의 mode로 계산하지 않습니다.

## 검증

- Replay: 433 accepted, 0 rejected
- Label leakage: PASS
- Production pipeline: PASS
- 전체 테스트는 커밋 전에 실행합니다.
