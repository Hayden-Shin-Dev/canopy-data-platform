# 구현 상태

기존 100단계 계획은 `docs/implementation_plan.md`에 유지한다. 실제 작업은 다음
브랜치 흐름으로 통합했다.

| 영역 | 브랜치 | 상태 |
|---|---|---|
| 기존 foundation·ingestion·mapping | `main`의 기존 단계 | 완료 |
| 문서 사용법 | `docs/ktdb` → `dev/ktdb-v1` | 완료 |
| population lookup·거리·모델 | `feature/ktdb-model` 등 → `dev/ktdb-v1` | 완료 |
| 재현 빌드·검증 | `feature/ktdb-validation` → `dev/ktdb-v1` | 완료 |
| blocker·release 기록 | `feature/ktdb-docs-final`, `feature/ktdb-release` | 완료 |

현재 `dev/ktdb-v1`에는 원본 ingestion부터 lookup, 선택적 centroid 거리, 학습·예측,
검증 CLI, 재현 스크립트가 들어 있다. `main`에는 release merge 전까지 기존 안정
상태를 유지한다.
