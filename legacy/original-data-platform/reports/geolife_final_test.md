# GeoLife 최종 Test 평가

Validation Macro F1 기준으로 선택한 120초 Window 무가중치 RandomForest를 Test Set에 평가했다. Test는 모델 선택 이후 독립적으로 실행했다.

- Window: 3,432개
- 사용자: 8명
- Accuracy: 0.6681
- Macro F1: 0.4715
- Weighted F1: 0.6676

## Class별 F1

- bike: 0.6879
- bus: 0.2087
- car: 0.5934
- rail: 0.0149
- walk: 0.8524

## Confusion Matrix

Class 순서는 `bike, bus, car, rail, walk`이다.

```text
[[368, 22, 125,   4,  48],
 [ 12, 43, 104,   8,  38],
 [ 60, 95, 556, 220, 108],
 [  5, 11,  15,   3, 133],
 [ 58, 36,  35,   2,1323]]
```

rail은 실제 167개 중 133개가 walk로, bus는 실제 205개 중 104개가 car로 예측됐다. car와 rail 사이에도 220개 혼동이 남아 있어 GPS-only Feature만으로 대중교통과 승용차를 안정적으로 구분하기 어렵다.

이 평가는 현재 Feature와 Window 정의에 대한 결과이며, 성능을 맞추기 위해 Test Set을 반복 튜닝하지 않았다.
