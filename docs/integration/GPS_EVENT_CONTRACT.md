# GPS Event Contract

Replay 입력과 향후 iPhone CoreLocation 입력은 같은 JSON event 계약을 사용합니다. 서버나 로컬 replay가 별도 형식으로 변환하지 않도록, 한 event가 관측된 순서 그대로 전달됩니다.

## Required fields

`schema_version`, `trip_id`, `device_id`, `sequence`, `timestamp`, `latitude`, `longitude`, `horizontal_accuracy_m`, `altitude_m`, `vertical_accuracy_m`, `speed_mps`, `course_deg`가 필요합니다. `source`와 `is_simulated`는 선택 필드입니다.

- `timestamp`: timezone을 포함한 ISO-8601 UTC. 저장 시 `Z`로 정규화합니다.
- `latitude`, `longitude`: WGS84(EPSG:4326) 십진수이며 각각 -90..90, -180..180 범위입니다.
- `sequence`: trip 안에서 0부터 시작하는 단조 증가 정수입니다. 중복·역순은 ingestion에서 거부합니다.
- 속도는 m/s, 정확도·고도는 m, course는 도(0 이상 360 미만)입니다.
- `horizontal_accuracy_m`, `vertical_accuracy_m`, `speed_mps`, `course_deg`의 `-1`은 iOS가 해당 값을 알 수 없다는 sentinel입니다. 이 값은 `null`과 경고로 정규화되며 실제 0 미만 값은 거부합니다.
- `altitude_m`의 `-9999`는 고도 무효 sentinel로 `null`과 경고로 정규화합니다. 해수면 아래의 실제 음수 고도는 허용합니다.

## CoreLocation mapping

향후 iOS 클라이언트는 `CLLocation`을 다음처럼 매핑합니다.

| iPhone 값 | event field |
| --- | --- |
| `CLLocation.timestamp` | `timestamp` (UTC) |
| `coordinate.latitude` / `longitude` | `latitude` / `longitude` |
| `horizontalAccuracy` | `horizontal_accuracy_m` |
| `altitude` | `altitude_m` |
| `verticalAccuracy` | `vertical_accuracy_m` |
| `speed` | `speed_mps` |
| `course` | `course_deg` |

`CLLocation`의 무효 sentinel은 위 규칙대로 보존 가능한 경고로 바꾸며, 위치 좌표와 timestamp가 무효이면 event 자체를 받지 않습니다. 실제 iPhone 전송 시에도 replay와 동일한 trip lifecycle과 event validation을 거칩니다.

JSON 예시는 [schemas/gps_event.schema.json](../../schemas/gps_event.schema.json)을 참고합니다.
