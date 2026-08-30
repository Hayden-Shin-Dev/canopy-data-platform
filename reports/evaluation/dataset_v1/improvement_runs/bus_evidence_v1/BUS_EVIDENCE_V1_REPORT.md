# Bus Evidence v1 Production Update 결과

상태: **RELEASE BLOCKED**

이번 작업은 main의 `7a193ed` (`integration-v1.0.1`)을 기준으로 `improve/bus-evidence-v1`에서 수행했다. 목적은 정류장 근접만으로 생기는 false bus를 줄이고 실제 bus evidence의 품질을 높이는 것이었다. Ground Truth는 inference에 사용하지 않았고 frozen `dataset_v1`도 수정하지 않았다.

## 후보 결과

현재 Production Final 기준은 Accuracy 0.7852, Macro F1 0.3921, Car F1 0.1745, Bus Precision 0.3528, Bus Recall 0.0702, Bus F1 0.1171이다.

- Candidate A: endpoint route consistency를 계산하도록 확장. 700/700 실제 검증 결과가 기준과 동일했다. Bus F1 0.1171, false bus 910으로 개선되지 않았다.
- Candidate B: bus stop radius 100m. bus/car subset 100개에서 Bus F1 0.2002였지만 전체 700개가 아니며, Release Candidate로 선택할 수 없다.
- Candidate C: endpoint route confirmation guard. bus/car subset 100개에서 Bus F1 0.0637로 기준보다 낮아 탈락했다.

Candidate B와 C의 subset 결과는 방향성 확인용으로만 보관했다. 전체 700개를 통과한 선택 후보가 없으므로 수치를 전체 성능으로 해석하지 않는다.

## 700개 검증

Candidate A는 8개 shard로 전체 700개를 실행했고 모든 shard가 failed 0이었다. frozen dataset hash validation도 PASS였다. 그러나 지표가 Production과 같아 개선 조건을 충족하지 못했다.

## Release Gate

| 조건 | 결과 |
| --- | --- |
| 700/700 평가 성공 | PASS |
| Bus Evidence precision 개선 | FAIL |
| Bus precision/recall/F1 개선 | FAIL |
| False Bus 감소 | FAIL |
| Car regression 없음 | PASS (Candidate A 기준 동일) |
| Rail P0 regression 없음 | PASS (Candidate A 기준 동일) |
| 전체 regression test | PASS (227 passed) |
| Ground Truth leakage 없음 | PASS |
| dataset_v1 변경 없음 | PASS |
| main 반영 | NOT RUN |
| Patch tag | NOT RUN |

Bus F1·Recall·Precision과 false bus가 동시에 좋아진 후보가 없으므로 Production 설정은 baseline 값으로 복원했다. 따라서 main merge와 `integration-v1.0.2` tag를 만들지 않았다.

## 다음 작업

다음 실험은 route/stop/direction/temporal evidence를 모든 window에 저장하는 P1-A 계측 단계다. 증거 품질을 측정할 수 있는 trace가 먼저 확보되어야 resolver threshold 변경을 안전하게 검증할 수 있다.
