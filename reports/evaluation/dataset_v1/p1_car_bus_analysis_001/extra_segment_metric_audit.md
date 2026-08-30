# Extra segment metric audit

두 보고서의 extra segment 수가 다른 것은 계산 오류라고 단정할 수 없다. 서로 다른 정의를 사용한다.

- Root Cause Analysis의 160건: `EXTRA_SEGMENT` 분류를 가진 journey 수. 기존 `multimodal_failure_analysis.csv`의 failure category 집계다.
- P0 improvement comparison의 baseline 174건: baseline Final sequence를 압축한 뒤 Ground Truth sequence보다 긴 journey 수.
- P0 improvement comparison의 updated 185건: 같은 sequence 길이 정의를 selected P0 결과에 적용한 journey 수.

따라서 160과 174/185는 분모와 판정 코드가 다르다. 174에서 185로 늘었다는 사실만으로 P0가 production segment logic을 악화시켰다고 결론내리지 않는다. 공통 evaluator 정의를 먼저 정한 뒤 별도 실험에서 재집계해야 한다. 이번 P1에서는 evaluator나 Production segment logic을 수정하지 않았다.

