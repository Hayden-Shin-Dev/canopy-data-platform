# Data Versioning Policy

## Raw data

`data/raw/<domain>/`은 외부에서 받은 원본을 보관하는 위치다. 파이프라인은 이
파일을 덮어쓰거나 정제하지 않는다. 원본의 출처, 다운로드 날짜, 파일 크기,
SHA256, 데이터 버전은 manifest 또는 해당 domain의 README에 기록한다.

KTDB CSV와 같이 GitHub 일반 파일 제한을 넘는 파일은 Git에 커밋하지 않는다.
원본이 필요한 실행자는 별도 전달 경로로 받은 파일을 `data/raw/ktdb/`에 배치한다.

## Interim and processed data

`data/interim/`과 대용량 `data/processed/` 결과는 Python 파이프라인으로 언제든
재생성할 수 있어야 하므로 기본적으로 Git 추적에서 제외한다. 작은 schema,
mapping, sample, metrics, 문서는 Git으로 관리한다.

수동으로 결과 CSV를 수정하지 않는다. 결과가 바뀌면 원본 버전이나 코드·설정·
스키마 변경을 먼저 기록하고 파이프라인을 다시 실행한다.

## Reproducibility

- 원본 manifest의 SHA256으로 입력 버전을 고정한다.
- 설정의 random seed와 의존성 범위를 기록한다.
- 실행 로그에는 입력 manifest, 코드 커밋, 출력 경로를 남긴다.
- 개인정보성 원본은 공개 저장소에 업로드하지 않는다.

