# P1-A Bus Evidence Stateful Experiment

## 기준

- Production commit: `7a193ed`
- Production tag: `integration-v1.0.1`
- Branch: `improve/bus-stateful-evidence-v1`
- Candidate evaluation: `candidate_700`
- Dataset: frozen `dataset_v1`, 700 journeys

## 구현

`src/transit_context/bus_state.py`에 window 간 Bus evidence를 누적하는 상태 머신을 추가했다. 상태는 `UNKNOWN`, `BUS_CANDIDATE`, `BUS_PROBABLE`, `BUS_CONFIRMED`로 구성하고 decay, persistence, hysteresis, release를 적용했다. 강한 stop proximity 하나만으로 Bus를 확정하지 않으며, confirmed Bus도 약한 근거가 두 번 이어질 때만 해제한다.

## 700개 결과

| Metric | Production | Stateful candidate | Difference |
|---|---:|---:|---:|
| Accuracy | 0.785198 | 0.785198 | +0.000000 |
| Macro F1 | 0.392119 | 0.392119 | +0.000000 |
| Bus F1 | 0.117064 | 0.117064 | +0.000000 |
| False Bus | 910 | 910 | +0 |
| Car F1 | 0.174511 | 0.174511 | +0.000000 |
| Rail F1 | 0.328001 | 0.328001 | +0.000000 |

후보와 baseline의 최종 prediction은 동일했다. 상태 전이도 `BUS_CANDIDATE` 이상 0회였으며, 상세 수치는 `bus_state_transition_metrics.csv`와 `bus_transition_timing.csv`에 남겼다.

## 원인 판단

주요 원인은 **Transit Context evidence 부족**이다. 현재 run에서 GT bus window의 bus context score 평균은 0.131, 75 percentile은 0.180이었다. 상태 머신의 첫 기준 0.35에도 이르지 못해 누적 로직이 실제 판정에 참여하지 못했다. 현재 데이터만으로 threshold를 낮추면 false Bus와 raw car 혼동을 다시 키울 위험이 있으므로 이번 release에는 반영하지 않았다.

## Release 결정

Release Gate는 **FAIL**이다. Bus F1 개선과 False Bus 감소가 동시에 발생하지 않았으므로 `main` merge 및 `integration-v1.0.2` tag를 생성하지 않는다. 다음 실험은 resolver threshold 반복 조정보다 Bus reference coverage와 raw GeoLife car/bus separability를 독립적으로 개선한 뒤 같은 frozen 700개로 재평가해야 한다.
