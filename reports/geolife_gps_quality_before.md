# GeoLife GPS 품질 분석 (Hardening 전)

분석 대상은 원본 `Geolife Trajectories 1.3.zip`과 기존 120초 Window Dataset이다. Raw는 수정하지 않고 strict=False parser가 건너뛴 행을 오류로 집계했다.

## Raw step

- 유효 point: 24,876,977개
- trajectory: 18,670개, 사용자 182명
- 연속 step: 24,858,307개
- parser 오류: 1건 (사용자 020의 좌표 범위 오류)
- zero dt: 698,900건
- negative dt: 0건
- 120초 초과 gap: 81,670건
- 100m/s 초과 speed: 51,719건
- 500m 초과 altitude jump: 1,923건

Speed 이상 예시는 사용자 000의 일부 trajectory에서 5~8초 사이 512~1,279m 이동으로 관측됐다. 이는 mode label을 사용하지 않고 좌표·시간만으로 확인한 값이다.

## 기존 processed Window

- 대상 Window: 119,260개
- NaN: 0개
- inf: 0개
- 중복 row: 0개
- 영향 사용자: 7명
- 영향 trajectory: 27개
- `valid_step_count == 0`: 24개
- `displacement_m > distance_m`: 14개
- `straightness_ratio > 1`: 3개

예를 들어 사용자 065의 `20110907100433` trajectory Window에서 `distance_m=57.18`, `displacement_m=57.51`, `straightness_ratio=1.0057`이 관측됐다. 동일 trajectory에는 valid step이 0인 Window도 존재한다.

이 결과를 기준선으로 삼아 다음 단계에서 mode-independent GPS quality policy를 코드와 config로 분리하고, filtered step sequence에서 Window Feature를 다시 계산한다.
