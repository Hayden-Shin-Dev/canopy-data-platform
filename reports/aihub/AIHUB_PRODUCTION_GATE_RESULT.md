# AI-Hub Production Gate Result

기준 branch: `feature/aihub-mobility-v2`

## Gate 결과

| 항목 | 결과 | 근거 |
|---|---|---|
| AI-Hub 실제 GPS primary benchmark | PASS | `AIHUB_EXPERIMENT_A_RESULTS.md` |
| Train/Validation/Test UID overlap | PASS (0/0/0) | `aihub_split_manifest.json`, release validator |
| 5개 class 존재 | PASS | release validator |
| Feature contract | PASS | `AIHUB_PRODUCTION_CONFIG.json`, release validator |
| Dataset / split manifest hash | PASS | release validator |
| 120초 window contract | PASS | release validator `--window-seconds 120` |
| Validation Accuracy >= 0.70 | PASS (0.7242) | `hist_120_linked_car_10000_metrics.json` |
| Test Accuracy >= 0.70 | PASS (0.7071) | `hist_120_linked_car_10000_metrics.json` |
| Validation Macro F1 >= 0.65 | PASS (0.7305) | `hist_120_linked_car_10000_metrics.json` |
| Test Macro F1 >= 0.65 | PASS (0.6992) | `hist_120_linked_car_10000_metrics.json` |
| Production replay | PASS | `reports/integration/validation.json` |
| Full regression suite | PASS (247 passed) | `python -m pytest -q` |
| v3 in model selection or gate | PASS (excluded) | `docs/evaluation/V3_BENCHMARK_DEPRECATION.md` |

## Champion

`models/mobility_recognition/aihub_hist120.joblib`

Current artifact: 10,000-file linked vehicle train-only augmentation, three windows per linked user. Validation-only probability calibration was evaluated but not promoted because it lowered the independent test Macro F1 on this larger sample.

HistGradientBoostingClassifier, seed 2021, 120초 aggregate window, 21개 AI-Hub feature, class weighting 없음. AI-Hub linked vehicle ZIP에서 사용자별 최대 3개 train window를 보강했습니다. 기존 `geolife_hardened_120s_purity_090.joblib`는 rollback artifact로 유지합니다. 모델 파일은 저장소 정책상 Git에 넣지 않으며 `scripts/rebuild_aihub_production.ps1 -VehicleArchives <zip>`로 재생성합니다.

## 주의

v3 synthetic 점수는 이 gate의 입력이 아닙니다. Mock replay의 실제 예측은 ground truth 보정 없이 기록되며, 별도 장기 iPhone 실측 데이터 수집은 운영 확장 과제로 남깁니다.
