# Mobility V4 후보 구조

V4는 기존 V3와 완전히 격리된 실험 후보다. 현재 구현된 부분은 공식 입력
계약을 검증하는 guardrail뿐이며, Production selector는 건드리지 않는다.

## 입력 흐름

`CoreLocation + CoreMotion + (검증된 AP/BTS)` → 공식 preprocessing 호환 표현
→ `340 × 60` → 공식 DenseNet checkpoint → 11개 logits → 검증된 label mapping
→ 선택적 Temporal/Transit 비교

AP/BTS 또는 공식 label-name 배열이 확인되지 않은 상태에서 누락 센서와 클래스를
임의로 합치지 않는다. `src/mobility_v4/contracts.py::validate_sample`은
GPS-only 샘플과 잘못된 shape를 거부한다.

## 실험 단계

1. Docker에서 Full modality standalone inference
2. Validation에서 Full / GPS+IMU / GPS-only modality ablation
3. 공식 11-class label 문서 확인 및 Canopy 5-class mapping 결정
4. UID/user-disjoint holdout에서 V3와 별도 비교
5. Movement only, +Temporal, +Transit, Final의 stage별 평가
6. 전환 latency, inference latency, regression 확인

Test set은 마지막 후보 평가에만 사용한다. 성능이 확인되기 전에는 `main`에
merge하거나 V3 artifact를 덮어쓰지 않는다.
