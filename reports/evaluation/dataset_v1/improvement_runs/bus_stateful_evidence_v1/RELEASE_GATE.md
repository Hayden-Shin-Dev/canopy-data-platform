# P1-A Stateful Bus Evidence Release Gate

상태: **FAIL**

| Gate | 기준 | 결과 |
|---|---|---|
| 700개 전체 평가 | 700/700 성공 | PASS |
| Bus F1 | baseline 0.117064 이상 | FAIL (0.117064, 개선 없음) |
| False Bus | baseline 910 미만 | FAIL (910) |
| Macro F1 | baseline 0.392119 이상 | PASS (0.392119, 개선 없음) |
| Car F1 guardrail | baseline 이상 | PASS |
| Rail F1 guardrail | baseline 이상 | PASS |
| Stateful state entry | 실제 candidate/probable/confirmed 진입 | NOT CAPTURED (기존 실행 trace에 상태 필드 없음) |
| Ground-truth leakage | 없음 | PASS |

## 결론

후보는 production 결과를 바꾸지 못했으며 release 조건을 충족하지 못했다. 따라서 `main` merge와 `integration-v1.0.2` tag 생성을 하지 않는다.

주요 원인은 **Transit Context만으로는 현재 synthetic GPS/reference에서 Bus evidence가 충분히 누적되지 않는 것**이다. 700개 평가의 bus context score 분포가 GT bus 평균 0.131, 75 percentile 0.180으로 낮았다. 이번 실행은 상태 telemetry 추가 전 evaluator로 수행되어 상태 진입률은 확인할 수 없었다. 이는 resolver threshold를 임의로 낮추는 문제보다 reference coverage와 raw car/bus 분리도를 먼저 보강하고, 다음 실행에서 상태 telemetry를 고정해야 한다는 근거다.
