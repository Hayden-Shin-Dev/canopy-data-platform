# 모델 템플릿

새로운 ML 예측 과제를 추가할 때 이 디렉터리 구조를 기준으로 사용합니다.

- `training/`: 모델 학습 코드
- `inference/`: 런타임 추론 코드
- `evaluation/`: 오프라인 평가
- `features/`: 해당 과제에 특화된 feature 로직
- `configs/`: 모델 및 학습 설정
- `tests/`: 모델별 테스트

여러 ML 과제에서 재사용하는 로직은 `ml/shared/`에 둡니다.
