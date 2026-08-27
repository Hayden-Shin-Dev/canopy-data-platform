# Canopy Population Mobility Pipeline

KTDB 2021년 개인통행실태조사 원본에서 Canopy의 Population Baseline과
Expected Behaviour Model용 데이터를 재현 가능하게 만드는 Python 3.11 프로젝트입니다.

원본 CSV는 `data/raw/ktdb/`에 그대로 두고, 아래 명령으로 중간·최종 산출물을 다시 만듭니다.

## 실행

```powershell
python -m pytest -q
python -m src.build_population_dataset
python -m src.validate_dataset
python -m src.train_expected_behaviour
```

기본 산출물은 `data/processed/population_baseline/ktdb/`에 생성됩니다.
원본에는 좌표가 없어 `od_straight_distance_km`와 `distance_band`는 현재 결측으로 남습니다.
대표좌표 CSV/XLSX가 준비되면 `--centroid-file` 옵션으로 같은 빌드에 연결할 수 있습니다.

모델 학습은 CatBoost가 설치된 환경에서 CatBoost를 사용하고, 미설치 환경에서는 sklearn fallback을 사용합니다.
식별자와 원시 응답 코드는 모델 입력에서 제외합니다.

## 디렉터리

```text
data/raw/        로컬 원본 데이터(버전 관리 제외)
data/processed/  전처리 산출물(코드로 재생성)
src/             데이터 빌드·학습·예측 코드
models/          학습 모델(코드로 재생성)
reports/         요약 및 평가 결과
tests/           핵심 변환 규칙 테스트
```
