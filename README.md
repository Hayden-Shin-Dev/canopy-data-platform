# GeoLife Mobility Recognition

## 목적

GeoLife GPS와 transportation label을 이용해 Canopy에서 실제 사용자의 이동수단을 판단할 Mobility Recognition Model을 만드는 작업입니다.

## 데이터

Microsoft Research GeoLife

## 목표 Mode

`walk`, `bike`, `car`, `bus`, `rail`

## 처리

Raw GPS → Label 연결 → GPS Feature → Window Dataset → Mobility Recognition → Segment → Multi-modal Trip Reconstruction

## 결과

현재는 원본 구조와 label 연결 품질을 확인한 단계입니다.

- trajectory: 18,670개, 182명
- GPS point: 24,876,978개(좌표 오류 1개 포함)
- label: 14,718개 row, 69명
- matched point: 5,372,735개
- ambiguous point: 67,880개
- unmatched point: 19,436,362개

## 현재 한계

- 원본 label에는 5개 target 외 mode도 존재합니다.
- 겹치는 label interval은 임의로 선택하지 않고 ambiguous로 남깁니다.
- 긴 sampling gap과 좌표 오류가 있어 전처리 규칙 검증이 필요합니다.
- 아직 Window Dataset과 Model은 만들지 않았습니다.

## 실행

구현 단계에서 필요한 명령을 추가합니다.
