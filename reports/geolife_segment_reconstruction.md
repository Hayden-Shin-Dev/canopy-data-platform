# GeoLife Multi-modal Segment 재구성

최종 Test Window(120초, 3,432개)에 선택 모델의 mode 예측을 user와 trajectory별로 정렬한 뒤, 같은 mode가 연속된 Window를 하나의 Segment로 합쳤다.

- 대상 trajectory: 146개
- 입력 Window: 3,432개
- 재구성 Segment: 1,044개
- Segment별 Window 수 합계: 3,432개

예측 Segment mode 분포:

- walk: 292
- bike: 209
- car: 309
- bus: 147
- rail: 87

각 Segment는 `user_id`, `trajectory_id`, 시작·종료 Window index, Window 수, 예측 mode를 보존한다. 따라서 하나의 trajectory 안에서 여러 mode가 이어지는 순서를 후속 Integration 단계에서 사용할 수 있다.

이번 검증은 Window 예측을 연속 구간으로 재구성하는 구조 검증이다. GPS-only Test 성능 자체는 [최종 Test 평가](geolife_final_test.md)에 기록한 수치와 동일하며, Segment 병합으로 정답 label을 새로 만들거나 성능을 부풀리지 않았다.
