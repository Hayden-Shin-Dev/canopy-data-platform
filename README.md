# Canopy Data Platform

Canopy는 친환경 이동을 했다는 이유만으로 보상하는 서비스가 아니라 비슷한 시간과 지역에서 사람들이 보통 어떻게 이동했는지와 사용자의 실제 이동을 비교해서 저탄소 방향으로 바뀌었는지를 계산한다 ( 궁극적 목표 )

## 지금까지 작업중 main에 들어온 작업

- KTDB 2021 데이터로 Expected Behaviour와 Population Baseline을 만들기
- GeoLife와 AI-Hub 실제 GPS로 이동수단을 예측
- 서울 버스, 지하철, 철도 reference로 GPS 결과를 보완
- GPS Replay로 iPhone 형식의 이벤트를 받아 120초 Window 단위로 처리
- Expected CO2, Actual CO2, CO2 Reduction과 Token Reward를 계산한
- Local UI에서 출근 전, 이동 중, 이동 완료 화면을 확인/테스트

## 사용한 데이터

KTDB 개인통행실태조사 2021 데이터는 Population Baseline에 사용

GeoLife는 초기단계에서 기본 GPS 이동수단 학습 데이터로 사용하였으나 문제가 발생하여 rollback 용으로만 남겨두었음

AI-Hub으로 데이터셋을 변경하여 교통수단 판별 데이터는 실제 GPS 원본에서 고정 120초 Window를 다시 만들고 학습 -- 예전에 사용하던 60초 요약 행 두 개를 합치는 방식은 train-serving skew가 있어서 production 경로에서 제거

서울 버스와 지하철 reference는 Transit Context(보조 역할)로 사용하고
`evaluation_dataset_v3`라는 gps genarator파일이 있는데 아직은 불완전하기 때문에 synthetic 평가용으로만 보관하고 학습이나 모델 선택에는 사용하지 않음

## 현재까지 타임라인

1. 기존 모델과 처리 경로를 먼저 확인
2. 학습과 runtime의 Feature가 같은지 비교
3. AI-Hub 원본 GPS에서 120초 Window와 canonical Feature 제작
4. 사용자 기준으로 Train, Validation, Test를 나누고 UID가 겹치지 않는지 확인
5. robust Feature와 cadence 학습 후보를 비교하고 Validation Macro F1로 모델을 골랐고
6. 실제 Test에서 Movement, Temporal, Transit, Final 단계를 각각 확인
7. Transit resolver가 고신뢰 rail 결과를 bus나 car로 바꾸던 문제를 수정
8. Mock GPS를 기존 Replay와 전체 Integration Pipeline에 넣어 결과를 확인
9. 전체 테스트를 돌린 뒤 main에 merge

## 최종 성능

최종 Test 단계 결과는 다음과 같습니다.

- Movement Accuracy: 0.6984
- Movement Macro F1: 0.6770
- Final Accuracy: 0.7080
- Final Macro F1: 0.6888
- walk F1: 0.839
- bike F1: 0.565
- car F1: 0.706
- bus F1: 0.629
- rail F1: 0.704

Validation Final Macro F1은 0.7307

Mock 결과는 `walk → rail → walk`로 나왔고, rail 구간은 서울 reference의 5호선으로 성공적으로 연결되어 출력됨.

상세 결과는 [AI-Hub runtime parity release](reports/aihub/AIHUB_RUNTIME_PARITY_RELEASE.md)와 [release checklist](reports/aihub/AIHUB_RUNTIME_PARITY_RELEASE_CHECKLIST.md)를 참조해주세요

## UI 확인 화면

현재 저장된 Local UI 확인 화면

### Home

![Canopy Home](reports/integration/screenshots/home.png)

### 이동 중

![Canopy Active Trip](reports/integration/screenshots/active.png)

### 이동 완료

![Canopy Result](reports/integration/screenshots/result.png)

## 실행 방법

저장소 루트에서 실행한다.

```powershell
python -m pip install -r requirements.txt
```

AI-Hub 모델을 새로 만들 때는 원본 데이터 경로를 지정한다.

```powershell
$env:AIHUB_DATA_ROOT = "C:\path\to\01-1.정식개방데이터"
.\scripts\rebuild_aihub_production.ps1
```

모델과 주요 reference를 확인한다.

```powershell
python scripts/validate_integration_artifacts.py
```

Mock GPS를 직접 확인한다.

```powershell
python -m scripts.evaluate_mock_trip --csv mock/canopy_iphone_mock_yeongdeungpo_to_microsoft.csv --ground-truth mock/canopy_iphone_mock_yeongdeungpo_to_microsoft_ground_truth.txt --output reports/aihub/AIHUB_RUNTIME_PARITY_MOCK_AFTER.json
```

Local UI를 실행한다.

```powershell
python scripts/run_integration_ui.py
```

브라우저에서 `http://127.0.0.1:8765`를 연다.

전체 테스트는 다음 명령으로 실행한다.

```powershell
python -m pytest -q
```


## Branch

모델 개선 과정과 평가 자료는 `feature/mobility-runtime-parity-v3`의 Git History에서 확인해주세요
