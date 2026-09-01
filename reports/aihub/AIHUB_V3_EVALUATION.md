# AI-Hub 후보 frozen v3 평가

후보 artifact를 고정한 뒤 frozen `evaluation_dataset_v3` 700개를 한 번 실행했습니다. 데이터 hash 검증은 2,100건 모두 PASS였고, 700개 journey가 모두 pipeline을 통과했습니다. Ground Truth는 inference에 전달하지 않았습니다.

평가 설정:

- candidate: `data/interim/aihub/rf_unweighted.joblib` (로컬 재생성 artifact)
- feature version: `aihub-window-v1`
- window: 60초
- evaluation commit: `592a5b8`
- 실행 시간: 2,355.796초

## 기존 v3 Production과 비교

| Stage | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| 기존 Production Movement ML | 0.5272 | 0.3197 | 0.5039 |
| 기존 Production Final Canopy | 0.5265 | 0.3452 | 0.5107 |
| AI-Hub 후보 Movement ML | 0.5068 | 0.4039 | 0.5580 |
| AI-Hub 후보 Final Canopy | 0.4640 | 0.3471 | 0.5016 |

AI-Hub 후보는 raw Macro F1은 0.0842 높아졌지만, 최종 Canopy Accuracy는 0.0625 낮아졌고 Weighted F1도 0.0091 낮아졌습니다. 따라서 전체 production 개선 gate를 통과하지 못했습니다.

## AI-Hub 후보 Final class F1

| Mode | F1 |
|---|---:|
| walk | 0.7613 |
| bike | 0.3134 |
| car | 0.1036 |
| bus | 0.2705 |
| rail | 0.2864 |

bus와 rail은 기존 final 결과보다 낮아졌고, car도 여전히 취약합니다. multimodal exact sequence는 140개 중 0개였습니다. 전체 confusion matrix와 transition 결과는 실행 디렉터리의 `confusion_matrix.csv`, `multimodal_metrics.json`, `transition_metrics.csv`에서 확인할 수 있습니다.

## Release 판정

`NOT READY`. AI-Hub ingestion, 사용자 분리, 모델 artifact, realtime adapter 자체는 동작하지만, 기존 production 대비 최종 결과가 전반적으로 개선되지 않았습니다. 이 후보를 main의 기본 모델로 교체하거나 release tag를 만들지 않습니다. 다음 개선은 별도 후보로 수행하고, 후보 선택 후 frozen v3를 다시 한 번만 평가해야 합니다.
