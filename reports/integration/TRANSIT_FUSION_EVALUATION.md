# Transit fusion 평가

서울에서 제공된 labelled fixture를 같은 production pipeline에 넣고, GeoLife raw mode와 Transit evidence를 반영한 fusion mode를 비교했다. fixture의 expected 값은 CSV에 넣지 않고 평가 스크립트의 외부 메타데이터로만 사용했다.

| Fixture | Expected | GeoLife raw | Fusion |
| --- | --- | --- | --- |
| seoul_bus_route.csv | bus | rail | car |
| seoul_car_no_transit.csv | car | rail | rail |
| seoul_subway_line1.csv | rail | rail | rail |
| seoul_walk_bike.csv | walk | walk | walk |

- Raw accuracy: 2/4 = 50%
- Fusion accuracy: 3/4 = 75%
- False rail raw: 2
- False rail fusion: 0
- Bike-labelled support: 0

따라서 rail fixture 확인과 car의 false rail 제거에는 도움이 됐지만 bus는 car로 오검출됐다. 제공된 fixture에는 bike 정답 trajectory가 없어 bike precision/recall은 `NOT TESTED`로 남긴다. 특정 노선이나 좌표를 이용해 결과를 보정하지 않았다.

## 재현

```powershell
python -m scripts.evaluate_transit_fusion
python scripts/validate_integration_artifacts.py
```

원시 결과는 `reports/integration/runs/transit_fusion_evaluation.json`에 저장된다.
