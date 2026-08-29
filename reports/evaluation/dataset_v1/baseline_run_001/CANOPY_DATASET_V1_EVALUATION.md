# Canopy dataset_v1 blind evaluation

Dataset: `C:\Users\user\Desktop\canopy-project-pt\data\evaluation\seoul-synthetic\evaluation_dataset_v1`
Canopy Baseline Commit: `0f252c19119de7b2c4f48be31623b88f7c675c01`
Evaluation Commit: `7b80bfc`
Ground Truth used during inference: **NO**
Total journeys: 700 / evaluated: 700 / failed: 0

## Raw GeoLife vs Final Canopy

| Metric | Raw GeoLife | Final Canopy | Difference |
| --- | ---: | ---: | ---: |
| Accuracy | 0.8067 | 0.6565 | -0.1502 |
| Macro Precision | 0.6083 | 0.4357 | -0.1726 |
| Macro Recall | 0.4380 | 0.3870 | -0.0510 |
| Macro F1 | 0.4080 | 0.2719 | -0.1361 |
| Weighted F1 | 0.8136 | 0.6975 | -0.1161 |

## Per mode F1

| Mode | Raw F1 | Final F1 | Difference |
| --- | ---: | ---: | ---: |
| walk | 0.9641 | 0.8803 | -0.0838 |
| bike | 0.4797 | 0.1240 | -0.3558 |
| car | 0.1884 | 0.1381 | -0.0503 |
| bus | 0.3757 | 0.0295 | -0.3461 |
| rail | 0.0319 | 0.1876 | 0.1557 |

## Final precision, recall, F1, and support

| Mode | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| walk | 0.9832 | 0.7969 | 0.8803 | 58225 |
| bike | 0.6052 | 0.0691 | 0.1240 | 5083 |
| car | 0.2385 | 0.0971 | 0.1381 | 2728 |
| bus | 0.2478 | 0.0157 | 0.0295 | 7068 |
| rail | 0.1040 | 0.9562 | 0.1876 | 2901 |

## Transit false positive / false negative

- False rail from car: 2056
- False rail from bike: 3752
- False rail from walk: 11387
- False bus from car: 186
- Rail false negative: 127
- Bus false negative: 6957

## Multimodal and transition evaluation

- Multimodal journeys: 200
- Exact sequence results: `multimodal_metrics.json`
- Segment and transition rows: `segment_metrics.csv`, `transition_metrics.csv`

## Hard case and noise evaluation

- Hard-case journeys: 140
- Hard-case results: `hard_case_summary.csv`
- Noise profile results: `noise_metrics.csv`

## Evaluation limitations

- The frozen dataset is a local read-only asset and is not committed.
- KTDB Expected Behaviour is included for production compatibility; mobility metrics score GeoLife and final resolver labels only.
- Multimodal, hard-case, noise, and failure details are in the machine-readable files in this directory.
- Time-weighted metrics use the fixed 120-second evaluation windows.
- Distance-weighted metrics are marked NOT AVAILABLE because the frozen Ground Truth does not provide per-segment distance weights.
