# Bus Evidence v2 Release Gate

Status: **BLOCKED**

The ordered progression candidate was evaluated on all 700 frozen journeys (76,005 windows, 700/700 successful, failed 0). It is not eligible for production release.

| Gate | Result | Evidence |
| --- | --- | --- |
| 700/700 evaluation | PASS | `candidate_ordered_700/summary.json` |
| Bus F1 improves | FAIL | `candidate_comparison.csv` (0.117064 -> 0.045455) |
| Bus evidence quality improves | FAIL | candidate precision/recall regress |
| False Bus decreases | PASS | 910 -> 159, but recall collapse makes this insufficient |
| Car guardrail | PASS | 0.174511 -> 0.226735 |
| Rail guardrail | PASS | 0.328001 -> 0.329121 |
| Macro F1 non-regression | FAIL | 0.392119 -> 0.387478 |
| Full regression | PENDING | run after candidate selection |
| Leakage / hardcoding | PASS | evaluator `ground_truth_used_by_inference=false`, dataset unchanged |

The candidate is rejected because the ordered-stop requirement suppresses nearly all true Bus windows. Production configuration was restored to the v1.0.1 defaults (`bus_require_ordered_progression=0`, `bus_use_ordered_progression_score=0`). No merge to `main` and no patch tag are allowed from this run.

Next experiment should improve Bus recall without allowing stop proximity alone to promote a non-Bus prediction; use a validation split or a reference with sufficient multi-stop observations before changing the resolver.
