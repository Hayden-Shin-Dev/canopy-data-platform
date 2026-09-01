# AI-Hub Real GPS Replay

이 기능은 기존 Demo Mock을 변경하지 않고, AI-Hub 실제 GPS trajectory를 현재 Production pipeline에 그대로 넣어 확인할 때 사용합니다.

## 준비

AI-Hub 원본은 Git에 넣지 않습니다. 로컬에 다음 구조가 있어야 합니다.

```text
<AI-Hub root>/Training/01.원천데이터/...
<AI-Hub root>/Validation/01.원천데이터/...
```

Production model과 split manifest는 먼저 준비되어 있어야 합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rebuild_aihub_production.ps1 `
  -VehicleArchives "C:\path\01.연계데이터_003.차량이동궤적_2.zip"
```

## Test case 선택

선택기는 `aihub_split_manifest.json`의 Test UID만 허용합니다. Train UID와 Validation UID는 즉시 거부하고, 모르는 UID도 거부합니다. 각 class에서 시간상 인접한 세 trajectory를 묶어 Production 120초 window가 닫히도록 합니다.

```powershell
python -m scripts.prepare_aihub_replay `
  "C:\path\01-1.정식개방데이터" `
  --windows data/interim/aihub/aihub_split_windows.csv `
  --split-manifest data/interim/aihub/aihub_split_manifest.json `
  --output data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --per-class 5
```

생성되는 manifest에는 raw 파일명, Test UID, class, point 수, 시간 범위와 파일 hash만 저장합니다. 원본 GPS는 복사하지 않습니다.

## 단일 trajectory replay

```powershell
python -m scripts.replay_aihub_test `
  "C:\path\01-1.정식개방데이터" `
  --manifest data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --replay-id WALK-01 `
  --speed instant `
  --output reports/aihub/AIHUB_REPLAY_WALK_01.json
```

`--speed`는 `1`, `5`, `10`, `30`, `instant`를 지원합니다. Replay 속도만 바뀌고 원래 GPS timestamp와 feature 계산은 바뀌지 않습니다.

출력에는 다음 단계가 따로 기록됩니다.

- Movement ML prediction과 실제 probability
- Temporal mode sequence
- Transit Context evidence
- Final prediction
- Ground Truth 비교 결과
- 거리와 CO2 결과

Ground Truth는 inference payload에 포함하지 않고, inference가 끝난 뒤 평가 필드에만 기록합니다.

## 25개 batch replay

```powershell
python -m scripts.replay_aihub_test `
  "C:\path\01-1.정식개방데이터" `
  --manifest data/replay/aihub_test/AIHUB_REPLAY_MANIFEST.json `
  --speed instant `
  --output reports/aihub/AIHUB_REPLAY_RESULTS.json
```

현재 로컬 Test 결과는 다음과 같습니다.

| Class | Cases | Movement correct | Final correct |
|---|---:|---:|---:|
| walk | 5 | 4 | 4 |
| bike | 5 | 5 | 5 |
| car | 5 | 0 | 2 |
| bus | 5 | 5 | 0 |
| rail | 5 | 3 | 0 |
| Total | 25 | 17 | 11 |

전체 pipeline은 19건이 `PASS`였고, 6건은 좌표가 현재 KTDB 행정동 mapping 범위 밖이라 `KTDB_CONTEXT_UNAVAILABLE`로 기록됐습니다. 이 6건에는 임의의 Expected Behaviour를 넣지 않았습니다. 원본 AI-Hub GPS를 서울 이동으로 가정하거나 Ground Truth에 맞추는 보정도 하지 않습니다.

상세 원본 결과는 `reports/aihub/AIHUB_REPLAY_RESULTS.json`에 있습니다.

## 기존 Mock과의 관계

기존 `mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv`와 Local UI 동작은 변경하지 않습니다. AI-Hub replay는 별도의 CLI와 manifest를 사용하며, 필요한 경우 같은 Production API/UI에 연결할 수 있습니다.
