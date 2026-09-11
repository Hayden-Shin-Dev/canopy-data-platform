# 데이터 디렉터리

현재 모노레포에서 사용하는 데이터 작업 공간입니다. 기존 프로토타입 데이터는 `legacy/original-data-platform/data/`에 보존합니다.

- `raw/`: 원천에서 받은 변경 전 데이터. 대용량 파일은 Git에 커밋하지 않습니다.
- `external/`: 외부 기관·공급자가 제공한 데이터 및 스냅샷.
- `interim/`: 전처리 또는 중간 변환 결과. 재생성 가능해야 합니다.
- `processed/`: 모델 학습·평가·서비스 입력에 사용할 최종 가공 데이터.
- `reference/`: 정류장, 행정구역, 코드표 등 비교적 안정적인 참조 데이터.
- `fixtures/`: 테스트에서 사용하는 작고 추적 가능한 샘플 데이터.

대용량 데이터셋은 Azure Blob Storage/Data Lake 등 외부 저장소에서 관리하고, 저장소에는 필요한 경우 README, manifest, schema, 소규모 fixture만 커밋합니다.
