# Canopy dataset_v1 blind evaluation

Dataset: `C:\Users\user\Desktop\canopy-project-pt\data\evaluation\seoul-synthetic\evaluation_dataset_v1`
Canopy Baseline Commit: `7a193ed`
Evaluation Commit: `57e8d4d`
Ground Truth used during inference: **NO**
Total journeys: 100 / evaluated: 100 / failed: 0

## Raw GeoLife vs Final Canopy

| Metric | Raw GeoLife | Final Canopy | Difference |
| --- | ---: | ---: | ---: |
| Accuracy | 0.3249 | 0.1652 | -0.1597 |
| Macro Precision | 0.2005 | 0.1807 | -0.0199 |
| Macro Recall | 0.1325 | 0.0767 | -0.0559 |
| Macro F1 | 0.1569 | 0.0963 | -0.0607 |
| Weighted F1 | 0.3917 | 0.2108 | -0.1808 |

## Per mode F1

| Mode | Raw F1 | Final F1 | Difference |
| --- | ---: | ---: | ---: |
| walk | 0.0000 | 0.0000 | 0.0000 |
| bike | 0.0000 | 0.0000 | 0.0000 |
| car | 0.3964 | 0.4176 | 0.0211 |
| bus | 0.3883 | 0.0637 | -0.3246 |
| rail | 0.0000 | 0.0000 | 0.0000 |

## Final precision, recall, F1, and support

| Mode | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| walk | 0.0000 | 0.0000 | 0.0000 | 0 |
| bike | 0.0000 | 0.0000 | 0.0000 | 0 |
| car | 0.5207 | 0.3485 | 0.4176 | 901 |
| bus | 0.3826 | 0.0348 | 0.0637 | 1266 |
| rail | 0.0000 | 0.0000 | 0.0000 | 0 |

## Transit false positive / false negative

- False rail from car: 301
- False rail from bike: 0
- False rail from walk: 0
- False bus from car: 71
- Rail false negative: 0
- Bus false negative: 1222

## Multimodal and transition evaluation

- Multimodal journeys: 0
- Exact sequence results: `multimodal_metrics.json`
- Segment and transition rows: `segment_metrics.csv`, `transition_metrics.csv`

## Hard case and noise evaluation

- Hard-case journeys: 20
- Hard-case results: `hard_case_summary.csv`
- Noise profile results: `noise_metrics.csv`

## Evaluation limitations

- The frozen dataset is a local read-only asset and is not committed.
- KTDB Expected Behaviour is included for production compatibility; mobility metrics score GeoLife and final resolver labels only.
- Multimodal, hard-case, noise, and failure details are in the machine-readable files in this directory.
- Time-weighted metrics use the fixed 120-second evaluation windows.
- Distance-weighted metrics are marked NOT AVAILABLE because the frozen Ground Truth does not provide per-segment distance weights.
