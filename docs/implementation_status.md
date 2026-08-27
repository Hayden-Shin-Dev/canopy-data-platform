# 구현 상태

기존 100단계 계획은 `docs/implementation_plan.md`에 유지한다. 실제 작업은 다음
브랜치 흐름으로 통합했다.

| 영역 | 브랜치 | 상태 |
|---|---|---|
| foundation·ingestion·mapping | `dev/ktdb-v1` → `main` | 완료 |
| lookup·거리·모델 | `dev/ktdb-v1` → `main` | 완료 |
| 재현 빌드·검증 | `dev/ktdb-v1` → `main` | 완료 |
| blocker·release 기록 | `dev/ktdb-v1` → `main` | 완료 |

현재 `dev/ktdb-v1`와 `main`에는 원본 ingestion부터 lookup, 선택적 centroid 거리,
학습·예측, 검증 CLI, 재현 스크립트가 들어 있다. KTDB v1 release merge가 완료된
상태이며 다음 데이터 영역은 별도 dev branch에서 시작한다.
