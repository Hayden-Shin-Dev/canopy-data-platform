# Integration 개선 최종 체크리스트

현재 상태는 `NOT COMPLETE`이다. FAIL 또는 NOT TESTED 항목이 남아 있어 PR #2를 merge하지 않는다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| GeoLife 3개 이상 모델 비교 | PASS | `GEOLIFE_MODEL_EXPERIMENTS.md` |
| GeoLife 5개 class 지표·Confusion Matrix | PASS | `GEOLIFE_MODEL_EXPERIMENTS.md`, selected metrics JSON |
| car 별도 검증 | PASS | GeoLife car F1 0.5032, report 표 |
| GeoLife production 모델 재현 | PASS | `scripts/rebuild_geolife.ps1` CatBoost 명령 |
| Mock bike 오검출 완화 | PASS | raw `walk -> bike -> walk`, final `walk -> rail -> walk`; `tests/test_integration_segments.py` |
| Transit labelled fusion 평가 | FAIL | raw/fusion 50%, false rail 2건; `TRANSIT_FUSION_EVALUATION.md` |
| Transit bike precision/recall | NOT TESTED | 제공된 labelled fixture의 bike support 0 |
| KTDB 후보 비교 | PASS | `KTDB_MODEL_EXPERIMENTS.md` |
| KTDB calibration 지표 | PASS | Brier 0.4458→0.4340, Log Loss 0.8321→0.8067 |
| 거리 합계와 Emission 회귀 | PASS | full pipeline replay, `tests/test_integration_pipeline.py` |
| Expected CO2와 UI 연결 | PASS | `mock_trip_evaluation.json`, pipeline CO2 fields |
| 5호선 하드코딩 검사 | PASS | `src/`, `scripts/`에서 특정 line/station/coordinate 상수 없음 |
| 전체 pytest | PASS | 210 passed |
| 다섯 mode labelled E2E | NOT TESTED | bike-labelled trajectory와 car/bus 정상 reference fixture 부족 |
| 실제 브라우저 Home/Active/Result 캡처 | NOT TESTED | 현재 세션에 브라우저 제어 도구 없음; 기존 캡처는 이전 UI 버전 |
| 장시간 실제 iPhone GPS | NOT TESTED | 실기기 입력 필요 |

## 재현 명령

```powershell
python -m scripts.experiment_geolife_candidates data/processed/mobility_recognition/geolife_120s_purity_090.csv reports/integration/runs/geolife_candidate_comparison.json
powershell -ExecutionPolicy Bypass -File scripts/rebuild_ktdb_model.ps1
python -m scripts.evaluate_transit_fusion
python scripts/validate_integration_artifacts.py
pytest -q
```
