# 최종 Before / After 비교

모델 선택은 validation split에서만 했고, 아래 Test 수치는 선택 후 한 번 평가한 결과다. 사용자 단위 split을 유지했으며 Mock ground truth는 inference에 전달하지 않았다.

| Metric | BEFORE | AFTER |
| --- | ---: | ---: |
| GeoLife Accuracy | 0.6942 | 0.7183 |
| GeoLife Macro F1 | 0.5330 | 0.5616 |
| GeoLife Weighted F1 | 0.6820 | 0.7056 |
| Walk F1 | 0.8841 | 0.8963 |
| Bike F1 | 0.5577 | 0.5560 |
| Car F1 | 0.4524 | 0.5032 |
| Bus F1 | 0.6008 | 0.6179 |
| Rail F1 | 0.1701 | 0.2346 |
| KTDB Accuracy | 0.6771 | 0.6852 |
| KTDB Macro F1 | 0.4106 | 0.4193 |
| KTDB multiclass Brier | 0.4458 | 0.4340 |
| KTDB Log Loss | 0.8321 | 0.8067 |
| Mock raw sequence | `walk -> bike -> walk` | `walk -> bike -> walk` |
| Mock final sequence | `walk -> bike -> rail -> walk` | `walk -> rail -> walk` |

## 해석

GeoLife는 CatBoost base feature가 validation Macro F1 기준으로 선택되어 전체 Test 지표와 car/rail F1이 개선됐다. Bike F1은 거의 같아 과장하지 않는다.

KTDB는 현재 fallback artifact와 HGB 후보를 비교해 선택 모델을 재생성했다. Brier와 Log Loss가 함께 낮아져 확률 품질도 개선됐지만, 별도 운영 calibration threshold는 아직 정의하지 않았다.

Mock의 실시간 raw sequence는 모델 출력 그대로 `walk -> bike -> walk`이고, 최종 sequence는 순서가 확인된 subway evidence와 짧은 저신뢰 전환 Window 정리를 적용한 `walk -> rail -> walk`다.

Transit labelled fixture 평가는 별도 파일의 4개 케이스에서 raw/fusion 모두 50%이며 false rail 2건이다. bike-labelled fixture가 없어 Transit 5-class 전체 평가는 아직 완료되지 않았다.
