# iOS UI handoff

이번 Local Prototype은 iPhone 화면 폭(390~430pt)을 기준으로 구성했습니다.
실제 앱에서는 `CLLocation`을 canonical GPS event로 변환한 뒤 동일한 ingestion
계약으로 전송합니다.

## 화면과 상태

| 화면 | Prototype 영역 | backend 값 |
| --- | --- | --- |
| Home | 오늘의 이동, 절감량, 거리 | `co2.reduction_co2e_g`, `distance_km` |
| Test Mode | fixture, replay speed, Start/Pause/Resume/Stop | `/api/fixtures`, `/api/start` |
| Active Trip | 현재 상태, GPS polyline, event table | `/api/status.events`, `status` |
| Trip Result | 실제/예상 mode, 배출량, 절감량 | `actual_behaviour`, `expected_behaviour`, `co2` |
| Developer Mode | 120초 Window, Transit, KTDB, raw debug | `/api/status.window_predictions`, `pipeline`, `raw_debug` |

## GPS event mapping

Swift `CLLocation`을 아래 canonical 필드로 변환합니다.

```swift
[
  "schema_version": "1.0",
  "trip_id": tripId,
  "device_id": deviceId,
  "sequence": sequence,
  "timestamp": ISO8601DateFormatter().string(from: location.timestamp),
  "latitude": location.coordinate.latitude,
  "longitude": location.coordinate.longitude,
  "horizontal_accuracy_m": location.horizontalAccuracy,
  "altitude_m": location.altitude,
  "vertical_accuracy_m": location.verticalAccuracy,
  "speed_mps": location.speed,
  "course_deg": location.course,
  "source": "ios_core_location",
  "is_simulated": false
]
```

`-1`과 `-9999` sentinel은 [GPS_EVENT_CONTRACT.md](GPS_EVENT_CONTRACT.md)의 규칙에
따라 `nil`로 정규화합니다. sequence는 0부터 증가시키고 timestamp는 timezone을
포함해야 합니다.

## 사용자/개발자 모드 분리

User Mode에는 mode label, ground truth, model feature JSON 입력을 노출하지 않습니다.
Developer Mode에서만 기존 KTDB feature contract와 pipeline raw output을 확인할 수
있습니다. `ground_truth.txt`는 평가 도구에서만 읽고 앱 payload에는 포함하지 않습니다.

## 실제 앱 전환 시 유지할 계약

- event 단위 전송과 ingestion의 중복·역순·좌표 검증
- 120초 Window가 닫힌 뒤에만 GeoLife prediction 표시
- Transit evidence와 model prediction을 함께 기록
- 모델 또는 필수 입력이 없으면 성공으로 꾸미지 않고 `WAITING`/`FAILED` 표시
- Trip 종료 시 backend가 계산한 distance, expected/actual CO2, reduction만 표시
