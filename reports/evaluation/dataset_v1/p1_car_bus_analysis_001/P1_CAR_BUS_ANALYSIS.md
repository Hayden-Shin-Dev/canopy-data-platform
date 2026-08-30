# P1 Car/Bus 분석

이 문서는 `eval/car-bus-p1-analysis`에서 수행한 진단 결과다. Production inference, KTDB, GeoLife, Transit resolver 코드는 수정하지 않았다. 기준 Production은 main의 `7a193ed` (`integration-v1.0.1`)이며, frozen `dataset_v1`의 700개 여정을 그대로 사용했다.

## 실행 결과

- 평가 여정: 700/700, 실패 0
- Ground Truth window 수: walk 58,225, bike 5,083, car 2,728, bus 7,068, rail 2,901
- Raw window prediction 분포: walk 56,731, bike 5,640, car 9,140, bus 4,447, rail 47
- P0 이후 Final 분포: walk 55,961, bike 2,373, car 4,538, bus 1,406, rail 11,727

Raw 전체 성능은 Accuracy 0.8067, Macro F1 0.4080, Weighted F1 0.8136이다. P0 Final은 Accuracy 0.7852, Macro F1 0.3921, Weighted F1 0.7895다. P0는 false rail을 줄이고 rail F1을 높인 변경이며, car/bus 성능을 개선한 변경은 아니다.

## Car/Bus 혼동

Raw Car는 walk 193, bike 546, car 1,118, bus 871, rail 0으로 예측됐다. Raw Bus는 walk 151, bike 2,263, car 2,491, bus 2,163, rail 0이었다. 따라서 Raw Car/Bus의 핵심 문제는 두 class가 서로 직접 혼동되는 것뿐 아니라, bus가 bike와 car로 넓게 분산되는 점이다.

Raw class metric은 car Precision 0.1223 / Recall 0.4098 / F1 0.1884, bus Precision 0.4864 / Recall 0.3060 / F1 0.3757이다. P0 Final은 car 0.1397 / 0.2324 / 0.1745, bus 0.3528 / 0.0702 / 0.1171이다. Final 단계에서 rail override가 적용되면서 car 485개, bus 1,667개가 Raw 정답에서 다른 mode로 깨졌다.

상세 수치는 [`raw_car_bus_confusion.csv`](raw_car_bus_confusion.csv), [`final_car_bus_confusion.csv`](final_car_bus_confusion.csv), [`car_bus_correctness_transition.csv`](car_bus_correctness_transition.csv)에 있다.

## Transit evidence 확인

현재 trace에 남는 bus 관련 실제 값은 `bus_context_score`, `bus_stop_proximity_score`, `bus_route_match_score`, `bus_sequence_score`, `matched_bus_route_id`, `matched_bus_route_no`, `matched_bus_stop_count` 등이다. 이 P1에서는 저장된 `bus_context_score`만 사용해 분석용으로 none(<0.25), weak(0.25 이상 0.55 미만), strong(0.55 이상) 세 구간을 만들었다. 이 구간은 Production threshold가 아니다.

Bus Ground Truth 7,068개 window 중 none 2,829개(40.03%), weak 4,239개(59.97%), strong 0개였다. 즉 현재 trace에서는 strong evidence가 한 번도 남지 않았다. `bus_context_score >= 0.25`의 전체 window 기준 precision은 4,239/46,813 = 9.06%이며, bus window 기준 proxy recall은 4,239/7,068 = 59.97%다. 이는 실제 bus 증거 precision이 아니라 현재 저장 score의 진단용 proxy다.

Bus evidence가 있었지만 Final이 bus가 아니었던 bus window는 rail 3,153, car 373, bike 343, walk 54, 합계 3,923개다. 반대로 false bus activation은 Ground Truth 기준 walk 44, bike 257, car 453, rail 156개였다. 이 결과만으로 evidence를 신뢰할 수 있는 bus 판정으로 승격하면 안 된다.

Car window의 bus score proxy 그룹은 evidence 있음 1,903개, 없음 825개다. Car가 정류장 인근에 있을 때도 bus score가 생기는 구조라서, 현재 resolver는 도로 주행과 bus 승차를 충분히 분리하지 못한다.

Evidence 생성 조건은 `src/transit_context/evidence.py`와 `src/integration/pipeline.py`에 정의돼 있다. 버스 정류장 반경, 시작·종료 정류장, route id/number 및 stop id의 일치, 관측 순서가 점수에 반영된다. 현재 trace에는 시간표, 진행 방향, 도로 일치 같은 추가 근거가 저장되지 않으므로 해당 누락 사유를 더 세분화해 추정하지 않았다.

## GPS feature overlap

Car와 Bus 각 100개 trip에서 실제 GPS로 계산한 feature를 비교했다. 평균 속도 범위 overlap은 0.939, 최대 속도 0.916, speed std 0.699, stop ratio 0.468, 평균 절대 가속도 0.682, distance 0.853, displacement 0.634, straightness 0.813, sampling interval 0.745였다. 평균값도 각각 3.85 대 3.96 m/s, 8.85 대 7.78 m/s로 가깝다. 단일 GPS 속도·정류장 근접 feature만으로 car/bus를 분리하기 어려운 근거다. feature를 변경하거나 학습에 재투입하지 않고 진단만 수행했다. 원자료는 [`car_bus_feature_overlap.csv`](car_bus_feature_overlap.csv)다.

## Hard case와 대표 실패

현재 frozen 시나리오에는 `car_near_station`, `car_past_bus_stops`, `car_waiting_near_stop`, `congested_car`, `slow_bus`, `long_stop_spacing`, `parallel_rail_bus`, `real_transfer` 등이 있다. P0 결과에서 `slow_bus`와 `long_stop_spacing`은 Final accuracy 0, `parallel_rail_bus`는 0.1429, `real_transfer`는 0.025였다. 대표 실패 trip 목록은 [`representative_bus_failures.json`](representative_bus_failures.json)과 [`representative_car_failures.json`](representative_car_failures.json)이다.

Bus 실패 원인은 raw가 car인 경우 2,491개(37.90%), raw가 walk/bike인 경우 2,414개(36.73%), Raw에서 맞았지만 transit override로 깨진 경우 1,667개(25.37%)였다. Car 실패는 raw가 bus 871개(41.60%), raw가 walk/bike 738개(35.24%), override로 깨진 경우 485개(23.16%)였다. Pareto 원자료는 [`bus_failure_pareto.csv`](bus_failure_pareto.csv), [`car_failure_pareto.csv`](car_failure_pareto.csv)다.

## Raw ML 문제와 Transit 문제의 분리

- Raw ML: bus window의 주요 오분류가 bike 2,263, car 2,491이고, car window도 bus 871개로 예측됐다. GPS feature overlap이 높아 Raw model 자체의 분리 문제가 확인된다.
- Transit: bus score가 있는 전체 window의 proxy precision이 9.06%이고, bus 정답인데 Final rail이 된 window가 3,153개다. 정류장 근접만으로는 보조 context가 충분하지 않다.
- 따라서 다음 개선은 Raw feature를 바로 바꾸기보다, evidence 구성요소를 관측·검증할 수 있게 하는 단계가 우선이다.

## Rail P0 확인

P0 이후 false rail activation은 17,195에서 4,008로 감소했고, rail F1은 0.1876에서 0.3280으로 증가했다. 반면 car에서 rail로 간 window 1,161개, bus에서 rail로 간 window 5,320개가 남아 있다. P0의 목적은 rail false activation 완화였으며, 이 P1은 해당 변경을 되돌리거나 추가 조정하지 않는다.

## Multi-modal extra segment 정의 차이

기존 root-cause 문서의 160건은 `EXTRA_SEGMENT` 분류를 가진 **여정 수**다. P0 비교 파일의 baseline 174건과 updated 185건은 압축된 Final mode sequence가 Ground Truth sequence보다 긴 **여정 수**다. 두 값은 집계 코드와 분류 정의가 달라 직접 비교할 수 없다. 자세한 내용은 [`extra_segment_metric_audit.md`](extra_segment_metric_audit.md)에 기록했다.

## P1 분할

- P1-A: Bus evidence 구성요소와 coverage 계측
- P1-B: Raw car/bus ML feature/model 실험
- P1-C: Bus resolver와 route/sequence 검증

현재 branch에서는 분석과 테스트만 수행했다. Production 반영, 모델 재학습, threshold 변경은 하지 않았다.

## 다음 실험 하나

다음 실험은 **P1-A: bus evidence 계측 보강 및 coverage 검증**으로 한다. 먼저 현재 trace에 component score와 matched stop/route 정보를 모든 window에 일관되게 남기고, 서울 공식 reference가 실제로 연결된 경우와 그렇지 않은 경우를 분리해 validation set에서 evidence precision/recall을 측정한다. 그 결과가 확보되기 전에는 resolver threshold나 Raw model을 조정하지 않는다. 실행 계획은 [`p1_priority_recommendation.md`](p1_priority_recommendation.md)에 있다.

