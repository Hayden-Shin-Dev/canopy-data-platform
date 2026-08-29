# Rail override candidate comparison

Evaluation-only replay over all stored dataset_v1 Production traces. Ground Truth is not used to alter inference.

| Candidate | Accuracy | Macro F1 | Weighted F1 | False rail |
|---|---:|---:|---:|---:|
| baseline | 0.6565 | 0.2719 | 0.6975 | 17195 |
| A_strict_score | 0.7995 | 0.4473 | 0.8139 | 1948 |
| B_consecutive_score | 0.7670 | 0.4136 | 0.7896 | 5511 |
| C_high_score | 0.8064 | 0.4071 | 0.8133 | 0 |

Selected candidate: **A_strict_score**

A raises the confirmation requirement for a non-rail Raw prediction before retaining a rail Final mode. It improves all aggregate metrics in this frozen replay and sharply reduces false rail activation.

This result is a candidate signal only. Production code is changed only after the candidate is implemented and full regression is run.
