# AI-Hub Mobility v2 Release Gate

기준 브랜치: `feature/aihub-mobility-v2`

기준 데이터: AI-Hub Training과 Validation에서 추출한 유효 GPS trajectory를 UID 기준으로 다시 나눈 split

## 확인된 항목

| 항목 | 상태 | 근거 |
|---|---|---|
| GPS/Label 파일 1:1 pairing | PASS | `docs/AIHUB_MOBILITY_DATA.md`, ingestion tests |
| 좌표·timestamp 품질 검사 | PASS | `data/interim/aihub/*profile.json` 재생성 명령, `tests/test_aihub_ingest.py` |
| 사용자 단위 disjoint split | PASS | `src/aihub/split.py`, `tests/test_aihub_split.py` |
| 5개 class mapping | PASS | `src/aihub/config.py`, `tests/test_aihub_filenames.py` |
| 후보 모델 비교 | PASS | `reports/aihub/AIHUB_MODEL_COMPARISON.md` |
| 확률 지표 기록 | PASS | validation/test Brier score, `src/aihub/training.py` |
| runtime feature/window 계약 | PASS | `src/aihub/runtime.py`, `tests/test_aihub_runtime.py` |

## 아직 통과하지 못한 항목

| 항목 | 상태 | 사유 |
|---|---|---|
| 독립적인 실제 한국 holdout | NOT READY | 현재 원본의 공식 Training/Validation UID가 겹쳐 새 split을 만들었지만, 외부 독립 holdout은 없음 |
| GeoLife와 동일 조건의 최종 비교 | NOT READY | AI-Hub 60초 window와 기존 GeoLife 120초 window가 달라 직접 교체 근거가 부족함 |
| rail 데이터 충분성 | NOT READY | rail 원본 중 좌표 결측 trajectory 비율이 높음 |
| 기존 production pipeline 교체 | NOT READY | 후보 artifact는 opt-in adapter에서만 사용하며 기본 GeoLife 경로는 유지 |
| frozen evaluation_dataset_v3 최종 평가 | PASS (gate FAIL) | 후보 고정 후 700개 실행, 700 PASS, 단 최종 metric 개선 조건 미충족 |
| main merge 및 release tag | BLOCKED | 위 gate 항목이 남아 있어 성능을 과장하지 않기 위해 반영하지 않음 |

## 후보 고정 후 v3 결과

후보를 고정한 뒤 frozen v3 700개를 실제 실행했습니다. 데이터 무결성은 PASS였지만 기존 Production 대비 최종 Accuracy와 Weighted F1이 하락하여 release gate는 여전히 BLOCKED입니다. 상세 수치는 `AIHUB_V3_EVALUATION.md`에 기록했습니다.

## 현재 결론

AI-Hub ingestion, 품질검사, 사용자 분리, feature 생성, 후보 학습, runtime 계약은 재현 가능한 상태입니다. 그러나 독립 holdout과 기존 production 회귀를 통과하지 않았으므로 이번 브랜치를 최종 서비스 모델로 표시하지 않습니다. 다음 단계는 별도 한국 holdout을 확보한 뒤 validation으로 후보를 고르고, 마지막 한 번만 frozen `evaluation_dataset_v3`에서 확인하는 것입니다.
