# Integration mock 입력

`canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`는 iPhone CoreLocation에 맞춘
label-free GPS event 입력입니다. production replay는 이 CSV의 GPS 필드만 읽습니다.

`canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt`는 개발자용 평가
메타데이터입니다. 모델 inference, Transit Context, UI의 입력으로 사용하지 않습니다.
Replay 종료 후 prediction timeline과 비교할 때만 별도로 읽습니다.

CSV에는 mode, segment, ground truth, expected mode 같은 정답 필드가 없어야 하며,
필수 canonical GPS 필드는 `schemas/gps_event.schema.json`과 동일해야 합니다.

실행 예:

```powershell
python scripts/replay_integration.py mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv --speed instant --pipeline
```
