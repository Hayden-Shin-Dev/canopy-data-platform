# Repository Structure

`canopy-data-platform`은 데이터 출처별 처리 코드와 산출물 영역을 분리한다.
현재 구현 대상은 KTDB뿐이지만, 다른 데이터셋이 추가되어도 KTDB 코드가 서로의
원본이나 모델 산출물을 덮어쓰지 않도록 도메인 경계를 유지한다.

```text
canopy-data-platform/
├── data/
│   ├── raw/
│   │   ├── ktdb/
│   │   ├── geolife/
│   │   ├── administrative_area/
│   │   ├── emission_factors/
│   │   └── route_reference/
│   ├── interim/
│   │   └── <domain>/
│   └── processed/
│       ├── population_baseline/
│       ├── mobility_recognition/
│       ├── carbon_reference/
│       └── demo/
├── src/
│   ├── common/
│   └── <domain>/
├── configs/
│   └── <domain>/
├── schemas/
│   └── <domain>/
├── models/
│   ├── expected_behaviour/
│   └── mobility_recognition/
├── reports/
│   └── <domain>/
├── notebooks/
├── docs/
└── tests/
    └── <domain>/
```

## 경계 규칙

- `data/raw/<domain>`은 외부에서 받은 원본만 보관하며 파이프라인이 수정하지 않는다.
- `data/interim/<domain>`은 재생성 가능한 중간 결과이며 기본적으로 커밋하지 않는다.
- `data/processed/<purpose>/<domain>`은 모델·서비스 입력 계약에 맞춘 결과를 둔다.
- `src/<domain>`에는 도메인 의미를 해석하는 코드를 두고 `src/common`에는 인코딩,
  경로, 로깅, 검증처럼 여러 도메인에서 재사용할 수 있는 기능만 둔다.
- `configs`에는 매핑·시간 구간·임계값을, `schemas`에는 입출력 컬럼 계약을 둔다.
- `models`에는 바이너리 모델과 모델 메타데이터를 분리한다. 모델 입력 Feature는
  `schemas`와 함께 버전 관리한다.
- `reports/<domain>`에는 실행별 metrics, 요약, 가정과 데이터 품질 결과를 둔다.
- `notebooks`는 탐색과 시각화 용도이며 재현을 위한 production 경로가 아니다.

현재 로컬 파일은 아직 기존 `data/raw` 위치에서 관리되고 있으므로, KTDB 구현
단계에서 `data/raw/ktdb` 계약으로 정리한다. 원본 파일명과 내용은 이동 외에는
변경하지 않는다.

