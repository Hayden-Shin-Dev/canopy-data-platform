# P1 우선순위 제안

## 하나의 다음 실험

P1-A로 `bus evidence` 계측과 coverage 검증을 먼저 진행한다.

현재 trace에는 `bus_context_score`는 있지만 component score의 존재 여부와 matched route/stop의 품질을 모든 window에서 비교할 수 있는 형태가 아니다. 분석용 proxy의 precision은 9.06%이고, bus Ground Truth 기준 proxy recall은 59.97%다. 이 상태에서 resolver threshold를 조정하면 정류장 인근 car/walk를 bus로 올릴 위험이 있다.

다음 실험에서는 Production 판정을 바꾸지 않고 다음을 validation 결과로만 기록한다.

1. bus stop proximity, route match, sequence, live evidence의 실제 존재 여부
2. matched route/stop id와 공식 서울 reference의 연결 여부
3. evidence가 있는 window의 Ground Truth별 precision/recall
4. bus와 car의 false activation 및 missed evidence

이 계측 결과가 확보된 뒤에만 P1-B Raw ML 실험 또는 P1-C resolver 검토를 선택한다. 이번 분석 branch에서는 Production code를 변경하지 않는다.

