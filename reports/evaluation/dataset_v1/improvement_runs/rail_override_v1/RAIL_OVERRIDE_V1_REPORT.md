# Rail override v1 improvement report

Baseline commit: 0f252c19119de7b2c4f48be31623b88f7c675c01
Candidate commit: f32fa5c
Dataset: frozen dataset_v1 (700 journeys)

| Metric | Baseline | Updated | Difference |
|---|---:|---:|---:|
| accuracy | 0.6565 | 0.7852 | +0.1286 |
| macro_precision | 0.4357 | 0.4552 | +0.0194 |
| macro_recall | 0.3870 | 0.4700 | +0.0830 |
| macro_f1 | 0.2719 | 0.3921 | +0.1202 |
| weighted_f1 | 0.6975 | 0.7895 | +0.0920 |

Selected candidate: A_strict_score

The candidate improves aggregate Accuracy, Macro F1, Weighted F1 and all five class F1 values while reducing false rail activation.

Only rail confirmation logic changed. Model, features, window size, smoothing architecture, dataset and Ground Truth were not changed.
