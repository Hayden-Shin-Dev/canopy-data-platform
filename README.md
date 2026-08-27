# Canopy Population Mobility Pipeline

KTDB 2021년 개인통행실태조사 원본에서 Canopy의 Population Baseline과
Expected Behaviour Model용 데이터를 재현 가능하게 만드는 Python 3.11 프로젝트입니다.

현재 구현 단계와 실행 방법은 후속 커밋에서 계속 보강합니다.

## 디렉터리

```text
data/raw/        로컬 원본 데이터(버전 관리 제외)
data/processed/  전처리 산출물(코드로 재생성)
src/             데이터 빌드·학습·예측 코드
models/          학습 모델(코드로 재생성)
reports/         요약 및 평가 결과
tests/           핵심 변환 규칙 테스트
```

