# Stateful Bus Evidence 후보

이번 실험은 `7a193ed` production 기준에서 진행했다. 단일 window의 Bus 판정을 바로 확정하지 않고 `UNKNOWN → BUS_CANDIDATE → BUS_PROBABLE → BUS_CONFIRMED` 상태를 누적·감쇠·해제하는 후보를 구현했다.

| Candidate | 전이 조건 | 누적 방식 | 기대 효과 | 결과 |
|---|---|---|---|---|
| Stateful accumulation | 점수 0.35/0.50/0.65, 확인 전 2회 positive | decay 0.80, 약한 근거 2회 후 release | 단발성 false bus 감소, 실제 bus 지속성 보존 | FAIL: prediction 변화 없음; 상태 telemetry는 미수집 |

실제 700개 평가에서 기존 context score가 대부분 0.05~0.30 범위에 머물렀고, prediction trace에는 상태 필드가 포함되지 않았다. 후보 prediction 결과는 production baseline과 동일했다. 임의 threshold 완화는 별도 근거 없이 precision/recall을 다시 훼손할 수 있어 적용하지 않았다.
