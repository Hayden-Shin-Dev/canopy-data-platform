# Mock GPS 입력

이 폴더에는 Local Integration을 확인하기 위한 iPhone 형식의 GPS 입력이 있습니다.

## 파일

- `canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`: 실제 Replay 입력입니다. mode나 정답 label을 넣지 않은 GPS Event만 포함합니다.
- `canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt`: 개발 평가용 정답 기록입니다. 모델 inference 입력으로 사용하지 않습니다.

CSV의 필드와 형식은 `schemas/gps_event.schema.json`을 따릅니다. 원본 Mock 파일은 수정하지 말고, 새로운 입력이 필요하면 별도 파일로 추가합니다.

## 실행

저장소 루트에서 실행합니다.

```powershell
python scripts/replay_integration.py mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv --speed instant --pipeline
```

속도를 늦춰 Event 흐름을 보려면 `--speed 1`, `--speed 5`, `--speed 10`, `--speed 30` 중 하나를 사용합니다.

Local User Mode에서 같은 입력을 사용하려면 다음을 실행합니다.

```powershell
python scripts/run_integration_ui.py
```

브라우저에서 `http://127.0.0.1:8765`를 열고 Home의 `출근 시작하기`를 누릅니다.

## 평가 결과

Ground Truth 비교는 `python scripts/evaluate_mock_trip.py`로 별도 실행합니다. 비교 결과는 `reports/integration/mock_trip_evaluation.json`에 저장됩니다.

Ground Truth는 결과를 맞추기 위한 보정에 사용하지 않습니다. 현재 Mock에서 확인된 기존 모델 결과는 `walk`, `bike`, `walk`입니다.
