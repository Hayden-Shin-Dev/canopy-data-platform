# iPhone 센서 호환성

공식 AI-Hub 모델에 필요한 센서를 iOS 공개 API 기준으로 검토한 결과다.
private API나 임의로 만든 센서 값을 사용하지 않는다.

| 센서/정보 | iOS 공개 API | 공식 입력과의 관계 | 판정 |
|---|---|---|---|
| 위도·경도·속도·course·고도·정확도·timestamp | CoreLocation `CLLocation` | GPS 원시 입력으로 사용 가능 | 직접 수집 가능 |
| 가속도·자이로·device motion·user acceleration·회전·중력·자세 | CoreMotion | 공식 IMU 파생값을 만들 후보 | 직접 수집 가능. 공식 100Hz/필드 정렬 재현 필요 |
| Wi‑Fi BSSID/AP 스캔 | 일반 iOS 앱 공개 API | 공식 `pre_ap`의 고유 BSSID 개수와 동일하게 보장할 수 없음 | 제한적/운영 환경 확인 필요 |
| 셀 ID(ci/pci)/BTS 이력 | 일반 iOS 앱 공개 API | 공식 `pre_bts` 입력과 동일한 값을 제공하지 않음 | 불가능에 가까움 |
| 라벨 | 앱 센서가 아님 | 학습·평가에만 사용 | 런타임 입력 금지 |

CoreLocation과 CoreMotion만으로는 공식 340채널 tensor를 완성할 수 없다.
Wi‑Fi/BTS를 0 또는 sentinel로 대체해 공식 모델이 동작한다고 보고하지 않는다.
향후 iOS adapter를 만들 때는 권한, 백그라운드 수집, sampling cadence, 기기별
센서 축을 별도로 검증해야 한다.
