# AI-Hub 실제 GPS Replay

기존 Demo Mock은 그대로 두고, AI-Hub의 실제 Test GPS trajectory를 현재 Production pipeline에 넣어 결과를 확인하는 기능입니다. Replay 전용 추론 로직이나 모델은 만들지 않고 기존 Replay Engine과 Movement ML, Temporal, Transit Context, KTDB, Emission 함수를 그대로 호출합니다.

## 준비

AI-Hub 원본 데이터는 용량과 이용 조건 때문에 Git에 넣지 않습니다. 로컬에서 다음처럼 원본 폴더를 준비합니다.

```text
<AI-Hub root>/Training/...
<AI-Hub root>/Validation/...
<AI-Hub root>/Test/...
```

Production model과 split manifest가 먼저 준비되어 있어야 합니다. Test UID만 replay에 사용할 수 있으며 Train/Validation UID와 알 수 없는 UID는 거부됩니다.

## Test trajectory manifest 만들기

```powershell
python -m scripts.prepare_aihub_replay `
  "C:\path\to\01-1.정식개방데이터" `
  --windows data/interim/aihub/aihub_split_windows.csv `
  --split-manifest data/interim/aihub/aihub_split_manifest.json `
  --output data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --per-class 5
```

현재 manifest는 5개 class(walk, bike, car, bus, rail)에서 각 5개씩, 같은 UID의 인접 trajectory를 묶어 Production 120초 window가 닫히도록 구성합니다. 원본 CSV는 복사하지 않고 파일명과 hash만 기록합니다.

## CLI에서 한 건 확인하기

```powershell
python -m scripts.replay_aihub_test `
  "C:\path\to\01-1.정식개방데이터" `
  --manifest data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --replay-id WALK-01 `
  --speed instant `
  --output reports/aihub/AIHUB_REPLAY_WALK_01.json
```

`--speed`는 `instant`, `1`, `5`, `10`, `30`을 지원합니다. 속도는 전송 간격만 바꾸며 원본 timestamp, 순서, 좌표는 바꾸지 않습니다.

결과 JSON에는 다음 단계가 함께 기록됩니다.

- Movement ML prediction과 실제 probability
- Temporal mode sequence
- Transit Context evidence
- Final prediction
- 사후 비교용 Ground Truth와 correct 여부
- GPS 거리와 CO2 결과

Ground Truth는 payload나 inference 함수에 전달하지 않고, 추론이 끝난 뒤 결과 비교에만 사용합니다.

## 25건 전체 확인하기

```powershell
python -m scripts.replay_aihub_test `
  "C:\path\to\01-1.정식개방데이터" `
  --manifest data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --speed instant `
  --output reports/aihub/AIHUB_REPLAY_RESULTS.json
```

현재 로컬 Test 결과:

| Class | Case | Movement 정답 | Final 정답 |
|---|---:|---:|---:|
| walk | 5 | 4 | 4 |
| bike | 5 | 5 | 5 |
| car | 5 | 0 | 2 |
| bus | 5 | 5 | 0 |
| rail | 5 | 3 | 0 |
| 합계 | 25 | 17 | 11 |

25건 결과는 `reports/aihub/AIHUB_REPLAY_RESULTS.json`에서 확인할 수 있습니다. 6건은 현재 GPS만으로 KTDB 행정/목적 조건을 만들 수 없어 `KTDB_CONTEXT_UNAVAILABLE`로 기록되며 Movement 결과는 보존됩니다. 이 샘플 결과를 전체 모델 성능으로 해석하거나 정답에 맞게 보정하지 않습니다.

## 웹 Developer Mode에서 확인하기

```powershell
python scripts/run_integration_ui.py
```

브라우저에서 `http://127.0.0.1:8765`를 열고 Developer를 누릅니다. `AI-Hub Real GPS Replay`에서 Test trajectory와 `AI-Hub dataset root`(원본 폴더)를 선택한 뒤 `AI-Hub 결과 확인`을 누르면 기존 Production pipeline의 구조화된 결과가 화면에 표시됩니다. User Mode의 Demo Mock 동작에는 영향을 주지 않습니다.

API로도 확인할 수 있습니다.

```powershell
# Test 목록
curl http://127.0.0.1:8765/api/aihub/manifest

# 한 건 실행
curl -X POST http://127.0.0.1:8765/api/aihub/replay `
  -H "Content-Type: application/json" `
  -d '{"replay_id":"WALK-01","source_root":"C:\\path\\to\\01-1.정식개방데이터","speed":"instant"}'
```

원본 AI-Hub 데이터는 로컬에만 두고, manifest·코드·검증 결과만 저장소에 커밋합니다.
