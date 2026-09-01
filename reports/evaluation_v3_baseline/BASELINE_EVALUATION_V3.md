# Seoul Synthetic Evaluation Dataset v3 Baseline

## 기준

- Dataset: `seoul_synthetic_evaluation_v3`
- Production commit: `7a193ed`
- Evaluation branch: `evaluation/seoul-synthetic-v3-baseline`
- GPS points: 370,650 (dataset manifest)
- Journeys: 698 passed / 2 failed of 700
- Ground Truth leakage: **NO**. Ground Truth is loaded only after production inference.
- Dataset files were not modified.

## Overall metrics

| Stage | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| Movement ML | 0.5272 | 0.3197 | 0.5039 |
| Final Canopy | 0.5265 | 0.3452 | 0.5107 |

## Per-mode final metrics

| Mode | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| walk | 0.9587 | 0.8942 | 0.9254 | 8707 |
| bike | 0.3345 | 0.3700 | 0.3514 | 1246 |
| car | 0.0925 | 0.4376 | 0.1527 | 889 |
| bus | 0.7143 | 0.0102 | 0.0202 | 5368 |
| rail | 0.2001 | 0.4469 | 0.2765 | 1969 |

## Confusion and stage attribution

`confusion_matrix.csv` is the final GT→Prediction matrix. `movement_ml_results.csv`, `transit_context_results.csv`, and `final_prediction_results.csv` retain the three stage views. `error_attribution.csv` records observed error categories without inventing labels.

## Multimodal and delay view

`multimodal_metrics.json`, `segment_results.csv`, and `transition_metrics.csv` contain journey timeline and transition results. The current Production evaluator uses fixed 120-second windows; a mode change inside a window is therefore reported at the next closed window.

## Failed journeys

`failed_journeys.csv` contains the two short trips that ended while the first 120-second window was still `COLLECTING`. They are not relabeled or padded.

## Q&A

- Movement ML is strongest on walk and bike, while bus and rail recall are the main weaknesses in this v3 baseline.
- Bus errors are primarily missed bus windows rather than false bus activation (`metrics.json`).
- Rail improves in Final Canopy when structured station evidence is available, but false rail and missed rail remain measurable.
- Transit Context changes some ML decisions, but does not remove the underlying car/bus and rail separability limits.
- The next model-training step is intentionally not part of this baseline run; this branch records the untuned Production behavior on v3.
