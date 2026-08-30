# Canopy dataset_v1 blind evaluation

Dataset: `C:\Users\user\Desktop\canopy-project-pt\data\evaluation\seoul-synthetic\evaluation_dataset_v1`
Canopy Baseline Commit: `7a193ed`
Evaluation Commit: `537ad33`
Ground Truth used during inference: **NO**
Total journeys: 700 / evaluated: 700 / failed: 0

## Raw GeoLife vs Final Canopy

| Metric | Raw GeoLife | Final Canopy | Difference |
| --- | ---: | ---: | ---: |
| Accuracy | 0.8067 | 0.7852 | -0.0215 |
| Macro Precision | 0.6083 | 0.4552 | -0.1531 |
| Macro Recall | 0.4380 | 0.4700 | 0.0320 |
| Macro F1 | 0.4080 | 0.3921 | -0.0158 |
| Weighted F1 | 0.8136 | 0.7895 | -0.0240 |

## Per mode F1

| Mode | Raw F1 | Final F1 | Difference |
| --- | ---: | ---: | ---: |
| walk | 0.9641 | 0.9585 | -0.0056 |
| bike | 0.4797 | 0.3825 | -0.0972 |
| car | 0.1884 | 0.1745 | -0.0139 |
| bus | 0.3757 | 0.1171 | -0.2586 |
| rail | 0.0319 | 0.3280 | 0.2961 |

## Final precision, recall, F1, and support

| Mode | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| walk | 0.9779 | 0.9399 | 0.9585 | 58225 |
| bike | 0.6009 | 0.2805 | 0.3825 | 5083 |
| car | 0.1397 | 0.2324 | 0.1745 | 2728 |
| bus | 0.3528 | 0.0702 | 0.1171 | 7068 |
| rail | 0.2046 | 0.8270 | 0.3280 | 2901 |

## Transit false positive / false negative

- False rail from car: 1161
- False rail from bike: 1891
- False rail from walk: 956
- False bus from car: 453
- Rail false negative: 502
- Bus false negative: 6572

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
