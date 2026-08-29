# dataset_v1 Root Cause Analysis

이 문서는 완료된 blind baseline 결과를 사후 분석한 Evaluation 전용 문서입니다.
Production Prediction Logic, dataset_v1, Ground Truth 정의는 변경하지 않았습니다.

## Baseline 확인

- Canopy Baseline Commit: `0f252c19119de7b2c4f48be31623b88f7c675c01`
- Evaluation Branch: `eval/seoul-synthetic-v1`
- Dataset: `C:\Users\user\Desktop\canopy-project-pt\data\evaluation\seoul-synthetic\evaluation_dataset_v1`
- Journeys: 700 / 700 성공
- Ground Truth inference leakage: NO
- GPS label leakage: NONE

## 핵심 결론

Raw GeoLife와 Final Canopy를 동일한 Ground Truth window 기준으로 비교했습니다.
Hybrid 단계가 전체 성능을 높였는지는 아래 전환 수치와 원인별 집계로 판단합니다.
Ground Truth는 Production inference가 반환된 뒤 평가 단계에서만 읽었습니다.

## Correctness transition

| Category | Count | Percentage |
|---|---:|---:|
| Kept Correct | 47163 | 0.6205 |
| Fixed by Final | 2738 | 0.0360 |
| Broken by Final | 14152 | 0.1862 |
| Still Wrong | 11952 | 0.1573 |

Net Correction: **-11414**
Helpful Intervention Rate: 0.1027
Harmful Intervention Rate: 0.5306

## Mode regression

| Mode | Kept | Fixed | Broken | Still wrong | Net |
|---|---:|---:|---:|---:|---:|
| walk | 46397 | 3 | 9018 | 2807 | -9015 |
| bike | 351 | 0 | 2221 | 2511 | -2221 |
| car | 263 | 2 | 855 | 1608 | -853 |
| bus | 107 | 4 | 2056 | 4901 | -2052 |
| rail | 45 | 2729 | 2 | 125 | 2727 |

## Mode metrics snapshot

| Mode | Raw F1 | Final F1 |
|---|---:|---:|
| walk | 0.9641 | 0.8803 |
| bike | 0.4797 | 0.1240 |
| car | 0.1884 | 0.1381 |
| bus | 0.3757 | 0.0295 |
| rail | 0.0319 | 0.1876 |

## Scenario별 성능

| Scenario | Windows | Raw accuracy | Final accuracy | Difference |
|---|---:|---:|---:|---:|
| bike | 2691 | 0.4326 | 0.1286 | -0.3040 |
| bus | 2355 | 0.2752 | 0.0463 | -0.2289 |
| car | 1920 | 0.3922 | 0.1344 | -0.2578 |
| multimodal | 59540 | 0.8462 | 0.6875 | -0.1587 |
| rail | 826 | 0.0085 | 0.8475 | 0.8390 |
| walk | 8673 | 0.9640 | 0.8712 | -0.0928 |

## Single-mode vs multimodal

| Scope | Journeys | Raw journey accuracy | Final journey accuracy |
|---|---:|---:|---:|
| multimodal | 200 | 0.0050 | 0.0250 |
| single_mode | 500 | 0.5020 | 0.4220 |

Multimodal journeys: 200
- Exact sequence and failure categories are in `multimodal_failure_analysis.csv`.
- Sequence matching is evaluated without changing the production segmenter.

| Failure type | Count |
|---|---:|
| EXTRA_SEGMENT | 160 |
| WRONG_INITIAL_MODE | 14 |
| MISSING_SEGMENT | 14 |
| TRANSITION_CORRECTION_OR_REGRESSION | 7 |
| MATCH | 5 |

## Hard cases

`hard_case_ranking.csv` lists observed hard-case groups and Raw/Final journey accuracy.

## Root cause Pareto

| Rank | Root cause | Mode | Count | Share |
|---:|---|---|---:|---:|
| 1 | RAW_ML | walk | 7370 | 0.2823 |
| 2 | TRANSIT_CONTEXT_OR_RESOLVER | walk | 4455 | 0.1707 |
| 3 | TRANSIT_CONTEXT_OR_RESOLVER | bus | 3540 | 0.1356 |
| 4 | RAW_ML | bus | 3417 | 0.1309 |
| 5 | TRANSIT_CONTEXT_OR_RESOLVER | bike | 2438 | 0.0934 |
| 6 | RAW_ML | bike | 2294 | 0.0879 |
| 7 | RAW_ML | car | 1783 | 0.0683 |
| 8 | TRANSIT_CONTEXT_OR_RESOLVER | car | 680 | 0.0260 |
| 9 | RAW_ML | rail | 125 | 0.0048 |
| 10 | TRANSIT_CONTEXT_OR_RESOLVER | rail | 2 | 0.0001 |

## Transit / confidence observations

Transit evidence levels are descriptive bins over stored trace scores (none < 0.25, weak 0.25–0.55, strong ≥ 0.55); they are not production thresholds.
False activation, missing evidence, and resolver changes are recorded in `transit_error_analysis.csv`.
Raw confidence analysis is NOT_AVAILABLE because the frozen trace stores only the selected raw mode, not class probabilities.

## Code locations (read-only mapping)

- Raw ML/window inference: `src/integration/geolife_adapter.py::infer_windows`
- Transit evidence/resolver: `src/integration/pipeline.py::build_transit_context`, `src/transit_context/resolver.py::resolve_mode`
- Smoothing/segmentation: `src/integration/segments.py::smooth_window_modes`, `src/integration/pipeline.py::run_full_pipeline`
- This analysis: `src/evaluation/root_cause.py`, `scripts/analyze_dataset_v1_root_cause.py`

## Improvement priorities (proposal only)

- P0: investigate resolver/transit false activations that turn correct walk or bike windows into rail.
- P1: investigate bus evidence coverage and Raw bus recall before changing any resolver behavior.
- P1: improve Raw car/bus/rail class separability with a new independent experiment branch.
- P2: evaluate transition timing and segmentation errors after P0/P1 changes.

No production change is made by this report. Any improvement must be evaluated in a separate branch against this frozen baseline.
