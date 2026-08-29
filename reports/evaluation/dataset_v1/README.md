# Seoul synthetic dataset_v1 evaluation

이 디렉터리는 `data/evaluation`에 로컬로 보관한 Frozen dataset_v1의 최초 blind baseline 결과입니다. Dataset 안에는 prediction이나 평가 결과를 쓰지 않습니다.

## 실행

저장소 루트에서 다음처럼 실행합니다.

```powershell
python scripts/evaluate_dataset_v1.py `
  --dataset-root data/evaluation `
  --run-dir reports/evaluation/dataset_v1/baseline_run_001 `
  --canopy-baseline-commit <dev/integration-v1 기준 SHA> `
  --evaluation-commit <evaluation 브랜치 SHA>
```

실행 중에는 `predictions.jsonl`, `prediction_traces.jsonl`, `checkpoint.json`이 갱신됩니다. 중단된 경우 같은 명령에 `--resume`를 붙여 이어서 실행할 수 있습니다.

## 평가 원칙

- GPS CSV를 먼저 Production Pipeline에 넣고, inference가 끝난 다음 Ground Truth를 읽습니다.
- Ground Truth 값은 feature, window, Transit, resolver, smoothing, final mode 계산에 전달하지 않습니다.
- `dataset_v1`의 GPS·Ground Truth·manifest는 read-only이며 Git에 커밋하지 않습니다.
- Raw GeoLife와 Final Canopy를 같은 window 단위로 비교하고, 5개 mode를 모두 집계합니다.

## 결과 파일

- `summary.json`: Dataset, Canopy 기준 커밋, 실행 수, leakage, 실패/skip 집계
- `version_freeze.json`: 모델 artifact hash, 설정, window·smoothing 기준
- `predictions.jsonl`: Journey별 Ground Truth와 Raw/Final 결과
- `prediction_traces.jsonl`: window별 raw/final/transit trace
- `metrics.json`, `per_class_metrics.csv`: 전체·class별 지표
- `confusion_matrix_raw.csv`, `confusion_matrix_final.csv`: 5×5 confusion matrix
- `confusion_matrix_raw.png`, `confusion_matrix_final.png`: 같은 matrix 시각화
- `multimodal_metrics.json`, `segment_metrics.csv`, `transition_metrics.csv`: multimodal 평가
- `hard_case_summary.csv`, `noise_metrics.csv`: hard case와 noise profile별 결과
- `top_errors.csv`, `error_analysis.csv`: 주요 오류와 실패 Journey
- `CANOPY_DATASET_V1_EVALUATION.md`: 사람이 읽는 요약 보고서

거리 가중 지표는 Frozen Ground Truth에 segment별 거리 가중치가 없어 `distance_weighted_metrics.json`에서 NOT AVAILABLE로 남깁니다.

