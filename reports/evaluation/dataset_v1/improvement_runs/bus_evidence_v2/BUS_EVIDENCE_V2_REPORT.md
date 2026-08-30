# Bus Evidence v2 Production Improvement

## 기준

- Production baseline: `main@7a193ed` (`integration-v1.0.1`)
- Branch: `improve/bus-evidence-v2`
- Dataset: frozen `dataset_v1` (700 journeys, unchanged)
- Ground Truth는 Production inference가 끝난 뒤 평가 단계에서만 join했습니다.

## 진단에서 확인한 문제

CSV reference의 `route_id`와 `stop_id`가 숫자로 읽히는 반면 GPS 관찰값은 문자열로 정규화되어, 선택된 route의 stop sequence가 항상 비어 있었습니다. 그 결과 route candidate는 계산되지만 ordered progression은 사용되지 않았습니다.

이번 버전은 route와 stop 식별자를 비교할 때 문자열로 정규화하고, 각 window에 실제 관찰된 route 후보·정류장 거리·순서 진행·방향·시간·속도 신호를 trace로 남깁니다. trace는 판단 결과를 바꾸지 않는 관찰용 데이터입니다.

## Baseline 700개 결과

| Metric | v1.0.1 |
| --- | ---: |
| Accuracy | 0.7852 |
| Macro F1 | 0.3921 |
| Walk F1 | 0.9585 |
| Bike F1 | 0.3825 |
| Car F1 | 0.1745 |
| Bus F1 | 0.1171 |
| Rail F1 | 0.3280 |
| Bus evidence proxy precision | 0.0817 |
| Bus evidence proxy recall | 0.4089 |

세부 진단은 `full_700/bus_analysis/` 아래 CSV와 JSON에 기록했습니다.

## 후보

`bus_require_ordered_progression` 후보는 정류장 순서가 실제로 관찰된 경우에만 Bus 승격을 허용합니다. 후보 결과는 동일한 700개 평가가 끝난 뒤 아래 파일에 추가됩니다.

- `candidate_comparison.csv`
- `RELEASE_GATE.md`

Gate를 통과하지 못하면 기본 설정으로 복원하며 main과 tag는 변경하지 않습니다.
