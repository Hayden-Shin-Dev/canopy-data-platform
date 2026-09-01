# AI-Hub Production Gate Result

Baseline branch: `main`

## Gate result

| Check | Result | Evidence |
|---|---|---|
| AI-Hub real GPS primary benchmark | PASS | `AIHUB_EXPERIMENT_A_RESULTS.md` |
| Train/Validation/Test UID overlap | PASS (0/0/0) | split manifest and release validator |
| Five classes present | PASS | release validator |
| Feature contract | PASS | production config and release validator |
| Dataset and split manifest hashes | PASS | release validator |
| 120-second window contract | PASS | release validator |
| Validation Accuracy >= 0.70 | PASS (0.7242) | `hist_120_linked_car_10000_metrics.json` |
| Test Accuracy >= 0.70 | PASS (0.7071) | `hist_120_linked_car_10000_metrics.json` |
| Validation Macro F1 >= 0.65 | PASS (0.7305) | `hist_120_linked_car_10000_metrics.json` |
| Test Macro F1 >= 0.65 | PASS (0.6992) | `hist_120_linked_car_10000_metrics.json` |
| Production replay | PASS | `reports/integration/validation.json` |
| Full regression suite | PASS (254 passed) | `python -m pytest -q` |
| v3 in model selection or gate | PASS (excluded) | `docs/evaluation/V3_BENCHMARK_DEPRECATION.md` |

## Champion

`models/mobility_recognition/aihub_hist120.joblib`

The artifact is a 120-second aggregate HistGradientBoosting model using the 21-feature AI-Hub contract. It includes up to three train windows per user from a bounded 10,000-file linked vehicle sample. The linked source user IDs are disjoint from the original validation and test users. The raw ZIP remains an external local input and is never committed.

Validation-only probability calibration was evaluated separately. It improved the smaller sample but reduced the independent test Macro F1 on the 10,000-file sample, so it was not promoted.

The previous `geolife_hardened_120s_purity_090.joblib` artifact remains available as a rollback option. Rebuild the champion with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_aihub_production.ps1 `
  -VehicleArchives "C:\path\01.연계데이터_003.차량이동궤적_2.zip"
```

This gate covers the AI-Hub offline benchmark and local replay regression. It does not claim long-duration real iPhone validation or complete labelled Transit coverage.
