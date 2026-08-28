# GeoLife 모델 비교

60초 Window와 동일한 사용자 Group Split을 고정한 상태에서 Validation 결과만 사용해 후보 모델을 비교했다. Test 결과는 최종 모델을 고른 뒤 한 번만 기준으로 사용한다.

| 후보 | 설정 | Validation Accuracy | Validation Macro F1 | Validation Weighted F1 |
| --- | --- | ---: | ---: | ---: |
| RandomForest | `class_weight=balanced_subsample` | 0.6973 | 0.6644 | 0.6926 |
| RandomForest | `class_weight=None` | 0.7008 | **0.6671** | 0.6965 |
| ExtraTrees | `class_weight=None` | 0.6995 | 0.6648 | 0.6959 |

## 선택

Validation Macro F1이 가장 높은 `RandomForestClassifier` (`class_weight=None`)를 GeoLife v1 후보로 선택한다. 이 설정은 가중치를 적용한 RandomForest와 ExtraTrees보다 Validation에서 모든 평균 지표가 같거나 높았다.

Test Set은 모델 선택에 사용하지 않았으며, 선택 모델 확정 후 최종 평가에서만 사용한다.

## 해석

class weight를 적용해도 Validation Macro F1이 개선되지 않았고, ExtraTrees도 추가 이득을 보이지 않았다. 따라서 다음 개선은 모델 종류를 바꾸기보다 Window 크기와 라벨·샘플링 품질을 검증하는 방향으로 진행한다.
