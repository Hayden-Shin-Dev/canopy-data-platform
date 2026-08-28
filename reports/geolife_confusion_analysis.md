# GeoLife baseline confusion 분석

대상은 사용자 기준 split의 Test 5,360개 Window입니다. class 순서는 `bike, bus, car, rail, walk`입니다.

## rail

실제 rail 301개 중 정답은 6개였습니다. 오분류는 walk 232개, bus 29개, car 22개, bike 12개 순입니다. rail은 현재 Feature에서 walk로 가장 많이 흘러가며, Test rail 사용자가 2명뿐이라는 split 표본 영향도 함께 존재합니다.

## bus

실제 bus 300개 중 정답은 80개였습니다. 오분류는 car 132개, walk 61개, bike 21개, rail 6개 순입니다. bus→car 혼동이 가장 크므로 GPS-only Feature만으로 두 mode를 안정적으로 분리하기 어렵다는 근거가 됩니다.

## car

실제 car 1,507개 중 오분류는 rail 327개, bus 179개, walk 174개, bike 112개였습니다. car가 rail과 bus로도 많이 이동해 대중교통 context가 없는 상태의 구조적 혼동을 확인할 수 있습니다.

## 결론

현재 confusion만으로 mapping 오류라고 단정할 수는 없습니다. mode별 사용자 수·Window 수는 별도 분석에서 확인했고, 다음 단계에서 Feature 분포와 label/window 손실 여부를 분리 검증합니다. car↔bus가 계속 높으면 Transit Context 필요성을 결과로 남깁니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_confusion `
  "data/processed/mobility_recognition/geolife_baseline_metrics.json"
```
