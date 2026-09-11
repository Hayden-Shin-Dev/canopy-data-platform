# GeoLife 최종 후보 Split Coverage

선택한 120초 Window Dataset에 60초 기준 user→split 매핑을 적용했다. 한 사용자의 Window는 하나의 split에만 포함된다.

| split | 사용자 수 | Window 수 | bike | bus | car | rail | walk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 45 | 102,025 | 11,997 | 25,427 | 20,625 | 14,376 | 29,600 |
| validation | 10 | 13,803 | 4,143 | 2,011 | 1,460 | 1,518 | 4,671 |
| test | 8 | 3,432 | 567 | 205 | 1,039 | 167 | 1,454 |

Mode가 모든 split에 존재하므로 label 자체가 특정 split에서 사라진 문제는 없다. 다만 최종 Test의 rail 167개와 bus 205개는 walk·car보다 적어 class imbalance와 작은 사용자 수가 성능 분산을 키울 수 있다. 이 조건은 임의 oversampling이나 user leakage 없이 그대로 평가했다.
