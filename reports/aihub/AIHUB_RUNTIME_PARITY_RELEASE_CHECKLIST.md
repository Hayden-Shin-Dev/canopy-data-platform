# AI-Hub raw 120초 release checklist

이 문서는 raw GPS 120초 Window와 runtime parity 변경만 검증한다. 전체 Canopy production readiness와는 구분한다.

| 항목 | 상태 | 근거 |
|---|---|---|
| 원본 GPS 출처와 UID split 보존 | PASS | `AIHUB_RUNTIME_PARITY_RELEASE.md`, split manifest |
| Train/Validation/Test UID overlap 0 | PASS | `AIHUB_RUNTIME_PARITY_RELEASE_GATE.json` |
| raw point 기반 고정 120초 Window | PASS | `AIHUB_PIPELINE_STAGE_EVALUATION_AFTER.json` |
| summary aggregation production 경로 제거 | PASS | `scripts/rebuild_aihub_production.ps1` |
| 학습/runtime canonical Feature parity | PASS | `tests/test_aihub_features.py`, `tests/test_aihub_runtime.py` |
| cadence stress 2/5/10초 측정 | PASS | `AIHUB_CADENCE_STRESS.json` |
| 120초 rolling history와 10초 stride | PASS | `tests/test_aihub_runtime.py` |
| 결측·중복·역행·gap GPS 처리 | PASS | `tests/test_aihub_runtime.py`, `tests/test_integration_replay_quality.py` |
| Movement → Temporal → Transit → Final 평가 | PASS | 단계별 JSON 3종 |
| Ground Truth inference leakage 없음 | PASS | 단계별 JSON policy, Mock after report |
| Mock 결과 `walk → rail → walk` | PASS | `AIHUB_RUNTIME_PARITY_MOCK_AFTER.json` |
| Validation Macro F1 개선 | PASS | 0.7261 → 0.7307 Final |
| Test Macro F1 개선 | PASS | 0.6770 → 0.6888 Final |
| rail Test F1 개선 | PASS | 0.6619 → 0.7041 |
| 전체 regression | PASS | `275 passed` |
| 장시간 실제 iPhone GPS | NOT TESTED | 실제 장시간 로그 미제공 |
| bike-labelled Transit 평가 | NOT TESTED | 공급 reference에 bike label 없음 |

NOT TESTED 항목은 데이터가 제공되기 전까지 보류한다. 따라서 이번 브랜치는 `PASS_WITH_LIMITATIONS`이며, 이 두 항목을 근거 없이 COMPLETE로 표시하거나 main에 자동 merge하지 않는다.
