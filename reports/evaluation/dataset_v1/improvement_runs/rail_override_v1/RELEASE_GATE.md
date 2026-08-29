# Rail override v1 release gate

This gate records the decision for the Production candidate after the frozen
dataset evaluation. It is intentionally separate from baseline_run_001.

| Check | Status | Evidence |
|---|---|---|
| Candidate branch created separately | PASS | improve/rail-override-v1 |
| Frozen dataset unchanged | PASS | dataset_v1 manifest and 1,400 GPS/GT hashes |
| Ground Truth leakage absent | PASS | full_run/summary.json |
| Candidate evaluated on 700 journeys | PASS | full_run/summary.json, 700/700, failed 0 |
| Accuracy improved | PASS | candidate_comparison.csv |
| Macro F1 improved | PASS | candidate_comparison.csv |
| Weighted F1 improved | PASS | candidate_comparison.csv |
| All five class F1 improved | PASS | mode_metric_comparison.csv |
| False rail activation reduced | PASS | rail_error_comparison.csv |
| Multimodal result checked | PASS | multimodal_observation.csv |
| Full regression suite | PASS | regression_test_report.md, 225 passed |
| Production import smoke | PASS | regression_test_report.md |
| Trip/station/dataset-specific hardcoding | PASS | resolver change uses config threshold only |
| Model/features/window/emission/reward/UI changed | PASS | version_info.json |

## Decision

Candidate A_strict_score is the selected Production candidate. The change adds
one versioned rail confirmation threshold and falls back to the Raw non-rail
mode when that confirmation is not strong enough.

Main integration is recorded by the signed merge commit after this candidate
passed the gate. A release tag is created only on that final main commit.
