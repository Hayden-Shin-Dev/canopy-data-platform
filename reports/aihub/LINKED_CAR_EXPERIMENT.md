# Linked vehicle augmentation experiment

## 목적

AI-Hub linked vehicle ZIP의 실제 GPS를 car 학습 보강에 사용해, 기존 120초 HistGradientBoosting 후보의 성능이 validation에서 개선되는지 확인했다. 원본 ZIP은 저장소에 복사하지 않았고, 사용자별 최대 3개 window만 train split에 추가했다.

## 데이터와 누수 방지

- 입력: `01.연계데이터_003.차량이동궤적_1.zip`에서 결정론적으로 앞 2,000개 파일을 읽음
- linked windows: 2,436개 train window
- split: linked user는 train에만 추가; 기존 AI-Hub validation/test는 변경하지 않음
- group overlap: 기존 AI-Hub user ID와 linked user ID overlap 0
- feature: 기존 `aihub-window-v1` 21개 feature만 사용
- station metadata: 사용하지 않음

## 결과

| Metric | 기존 Hist 120 aggregate | linked car train3 | 변화 |
|---|---:|---:|---:|
| AI-Hub validation Accuracy | 0.7235 | 0.7280 | +0.0045 |
| AI-Hub validation Macro F1 | 0.7276 | 0.7295 | +0.0019 |
| AI-Hub test Accuracy | 0.7027 | 0.7074 | +0.0048 |
| AI-Hub test Macro F1 | 0.6914 | 0.6959 | +0.0045 |

car test F1은 0.7101에서 0.7195로 상승했고, bus F1도 0.5896에서 0.5982로 상승했다. rail F1은 0.6901에서 0.6875로 소폭 낮아져 추가 확인 대상으로 남긴다. 전체 결과와 confusion matrix는 `data/interim/aihub/hist_120_linked_car_train3_metrics.json`에 있다.

## 판단

Validation Macro F1이 개선됐고 release threshold도 유지하므로 이 후보를 다음 production candidate로 선택한다. 전체 linked archive를 무리하게 학습에 넣지 않고, `scripts/rebuild_aihub_linked_car_candidate.ps1`의 bounded sample 정책을 그대로 재현한다.
