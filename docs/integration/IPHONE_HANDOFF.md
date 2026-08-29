# iPhone handoff

화면별 state와 SwiftUI 전환 기준은 [IOS_UI_HANDOFF.md](IOS_UI_HANDOFF.md)에 정리했습니다.

## Data path

현재 로컬 replay는 `ReplayEngine.stream()`으로 event를 하나씩 `TripIngestor.ingest()`에 전달합니다. 향후 iOS 앱도 같은 ingestion 함수를 호출하는 HTTP adapter를 사용하며, payload의 필드명과 검증 규칙은 바꾸지 않습니다.

권장 외부 endpoint는 `POST /api/v1/gps/events`입니다. 이 저장소의 local UI는 개발용 fixture control endpoint만 제공하고, production HTTP server는 아직 범위에 포함하지 않습니다.

## CoreLocation mapping

`CLLocation.timestamp`, `coordinate.latitude/longitude`, `horizontalAccuracy`, `altitude`, `verticalAccuracy`, `speed`, `course`를 각각 canonical GPS Event의 동일한 필드로 변환합니다. timezone은 UTC ISO-8601로 보내고, `CLLocation`의 -1 무효 값은 계약에 정의한 sentinel로 보냅니다.

```swift
let event: [String: Any] = [
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

## Lifecycle

앱은 trip 생성 후 sequence를 0부터 증가시키며 event를 전송합니다. ingestion은 중복·역순·좌표 오류를 거부하고 gap/jump/정확도 경고를 기록합니다. stop 이후 `PROCESSING`에서 120초 window, GeoLife inference, Seoul Transit Context, KTDB Expected Behaviour, Emission 계산을 수행하고 결과를 저장합니다. 모델 artifact나 필수 조건이 없으면 성공으로 대체하지 않고 `FAILED` 또는 `WAITING`으로 남깁니다.

상세 필드는 [GPS_EVENT_CONTRACT.md](GPS_EVENT_CONTRACT.md), JSON Schema는 [schemas/gps_event.schema.json](../../schemas/gps_event.schema.json)입니다.
