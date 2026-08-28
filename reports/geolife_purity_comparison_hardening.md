# GeoLife Window Label Purity 비교

GPS quality hardening 후 120초 Dataset에서 label purity filtering을 비교했다. 모델 입력에는 purity 파생값을 포함하지 않아 label leakage를 막았다. 사용자 Group Split과 RandomForest 설정(무가중치, 100 trees, seed 2021)은 동일하다.

| 조건 | Window 수 | Validation Accuracy | Validation Macro F1 | Validation Weighted F1 |
| --- | ---: | ---: | ---: | ---: |
| 무필터 | 115,560 | 0.6921 | 0.6092 | 0.7045 |
| purity ≥ 0.8 | 114,250 | 0.6956 | 0.6131 | 0.7067 |
| purity ≥ 0.9 | 113,718 | **0.6969** | **0.6146** | **0.7092** |

purity ≥ 0.8은 1,310개, ≥0.9는 1,842개 Window를 제외해 각각 전체의 98.9%, 98.4%를 유지한다. 두 기준 모두 품질이 낮은 transition Window를 줄이면서 Validation 지표가 소폭 상승했다.

## 선택

GeoLife v1.1 후보는 purity ≥ 0.9 설정으로 기록한다. 다만 threshold는 설정값이며 Dataset에 purity를 계속 보존한다. 이후 서비스 요구사항이 달라지면 무필터 또는 0.8 기준을 동일 코드로 재생성할 수 있다. Test Set은 이 선택에 사용하지 않았다.
