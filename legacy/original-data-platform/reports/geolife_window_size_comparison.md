# GeoLife Window 크기 비교

30초, 60초, 120초 Window를 같은 원본·라벨 조건(`min_points=2`, `label_coverage=0.5`)으로 생성했다. 30초와 120초는 60초 결과의 user→split 매핑을 재사용해 사용자 Group Split 차이를 줄였다.

| Window | 선택 Window 수 | Validation Accuracy | Validation Macro F1 | Validation Weighted F1 |
| ---: | ---: | ---: | ---: | ---: |
| 30초 | 392,717 | 0.6760 | 0.6427 | 0.6717 |
| 60초 | 213,549 | 0.7008 | 0.6671 | 0.6965 |
| 120초 | 119,260 | **0.7203** | **0.6898** | **0.7166** |

## 선택

Validation Macro F1이 가장 높은 120초 Window를 다음 모델 개선과 최종 후보에 사용한다. 긴 Window가 이동 중 속도·방향 정보를 더 안정적으로 집계한 것으로 보이지만, 이는 Validation 결과에 대한 관찰이며 Test Set으로 선택하지 않았다.

30초와 120초의 Test 지표는 참고로만 기록한다(각각 Accuracy 0.5898 / Macro F1 0.4294, 0.6681 / 0.4715). 최종 모델 확정 후 Test 평가를 별도로 수행한다.
