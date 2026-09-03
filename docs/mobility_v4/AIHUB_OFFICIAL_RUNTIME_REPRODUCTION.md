# Mobility V4 공식 런타임 재현

이 문서는 `feature/mobility-multimodal-v4`에서 공식 AI-Hub 체크포인트를
원본 방식으로 실행하기 위한 절차와 현재 상태를 기록한다. V3 Production
artifact는 변경하지 않는다.

## 현재 상태

`reports/mobility_v4/OFFICIAL_MODEL_SMOKE.json`의 상태는 `BLOCKED`다.
Windows 개발 환경에서 Docker CLI는 설치돼 있지만 Docker daemon이 실행되지
않아 공식 이미지를 실행할 수 없었다. 따라서 checkpoint load 이후의 실제
preprocessing, tensor inference, output class, latency는 아직 측정하지 않았다.

체크포인트 자체는 읽기 전용으로 검사했고, Lightning archive와
`model.fc.weight` 항목이 존재함을 확인했다. 원본 `last.chk`나 12GB Docker
이미지는 저장소로 복사하지 않았다.

## 재현 명령

Docker Desktop Linux engine을 시작한 뒤 저장소 루트에서 실행한다.

```powershell
$env:AIHUB_OFFICIAL_ROOT = "C:\Users\user\Downloads\교통수단 ai모델\AI모델\AI모델 교통수단 판별 20231207"
python -m scripts.run_aihub_official_smoke `
  --official-root $env:AIHUB_OFFICIAL_ROOT `
  --output reports/mobility_v4/OFFICIAL_MODEL_SMOKE.json
```

이 명령은 daemon이 없을 때 exit code 2와 `BLOCKED`를 반환한다. 센서나
checkpoint를 임의 값으로 채우지 않는다. 실제 공식 `run.sh` 재현은 Docker
이미지 로드 후 공식 안내의 `/ml/data/origin/3.Test` 마운트 명령으로 별도
수행해야 한다.

## 고정해야 할 계약

- 공식 입력: 340 channels × 60 timesteps
- 공식 출력: 11 logits
- modality: GPS, IMU, Wi‑Fi/AP, BTS/cell
- observation duration: 공식 preprocessing의 실제 sampling 간격을 실행 로그로
  확인하기 전에는 초 단위로 단정하지 않는다.

실제 inference가 성공하면 이 문서와 JSON에 입력·출력 shape, 예측 class,
CPU/GPU, latency를 추가한다. 그 전에는 V4 selector나 기존 UI를 변경하지 않는다.
