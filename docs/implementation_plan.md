# KTDB Population Baseline Implementation Plan

이 문서는 KTDB 2021 원본에서 Canopy Population Baseline과 Expected Behaviour
Model용 산출물을 재현하는 작업을 100개의 독립적인 개발 단위로 나눈 계획이다.
각 단계는 실제 변경과 검증을 수행한 뒤 하나의 Conventional Commit으로 남긴다.
커밋 날짜나 작성자를 조작하지 않으며, 대용량 원본과 생성 산출물은 Git에 넣지 않는다.

## 운영 원칙

- 원본 흐름은 `data/raw/ktdb → data/interim/ktdb → data/processed/population_baseline/ktdb`로 유지한다.
- 모든 컬럼 의미와 코드값은 `Code book.xlsx`에서 확인한다.
- 개인식별자와 개인정보성 응답은 모델 입력에서 제외한다.
- 좌표 원본이 없으면 가짜 좌표를 만들지 않는다. 거리 단계는 `blocked`로 기록하고 좌표 없이 가능한 단계부터 진행한다.
- 각 단계 시작 시 `git status`, diff, 기존 코드를 확인하고, 단계 종료 시 테스트와 재현 명령을 실행한다.

## 단계 목록

| Step | 작업 내용 | 예상 변경 파일 | 검증 방법 | 예상 Commit Message |
|---:|---|---|---|---|
| 001 | 전체 구현 계획과 단계 운영 규칙 문서화 | `docs/implementation_plan.md` | 문서에 100개 단계와 거리 blocker 확인 | `docs: add KTDB implementation plan` |
| 002 | 장기 다중 데이터셋 디렉터리 정책 확정 | `docs/repository_structure.md` | KTDB·향후 도메인 경로 충돌 검토 | `docs: define multi-source repository layout` |
| 003 | 원본·중간·산출물 Git 추적 정책 문서화 | `.gitignore`, `docs/data_policy.md` | 대용량 파일 ignore 패턴 검사 | `docs: document data versioning policy` |
| 004 | KTDB 원본 디렉터리와 파일명 계약 정의 | `data/raw/ktdb/README.md` | 필수 파일 목록과 불변성 확인 | `docs: define KTDB raw data contract` |
| 005 | 원본 파일 발견 및 존재 여부 검사기 추가 | `src/common/file_inventory.py` | 누락·추가 파일 경고 테스트 | `feat: add raw file inventory` |
| 006 | 원본 파일 크기·SHA256 manifest 생성기 추가 | `src/common/manifest.py` | manifest 해시 재계산 일치 확인 | `feat: add raw data manifest` |
| 007 | manifest 출력 스키마 고정 | `schemas/raw_manifest.schema.json` | JSON schema 검증 | `feat: define raw manifest schema` |
| 008 | CP949/UTF-8 자동 인코딩 탐지 함수 추가 | `src/common/encoding.py` | 두 인코딩 샘플 판별 테스트 | `feat: detect KTDB CSV encoding` |
| 009 | 공통 경로 및 환경 설정 모듈 추가 | `src/common/paths.py`, `src/config.py` | 기본 경로가 저장소 루트 기준인지 확인 | `feat: centralize pipeline paths` |
| 010 | 로깅 설정과 CLI 공통 옵션 추가 | `src/common/logging_utils.py` | `--help`와 로그 출력 확인 | `feat: add pipeline logging configuration` |
| 011 | Code Book workbook 시트 발견기 추가 | `src/ktdb/codebook.py` | 기본·이동·Value 시트 감지 | `feat: discover KTDB codebook sheets` |
| 012 | Code Book 변수 레이블 로더 추가 | `src/ktdb/codebook.py` | `TP2`, `TP5_1`, `DATE` 레이블 확인 | `feat: load KTDB variable labels` |
| 013 | Code Book 값 사전 로더 추가 | `src/ktdb/codebook.py` | 목적·수단 코드 사전 확인 | `feat: load KTDB value dictionaries` |
| 014 | Code Book 코드 타입 정규화 | `src/ktdb/codebook.py` | 숫자·문자·공백 코드 동일성 테스트 | `fix: normalize KTDB code values` |
| 015 | Code Book parser 단위 테스트 추가 | `tests/test_codebook.py` | 실제 workbook fixture로 통과 확인 | `test: cover codebook parsing` |
| 016 | 행정동 workbook 컬럼 발견기 추가 | `src/ktdb/admin_area.py` | 행정동 코드·시도·시군구 컬럼 확인 | `feat: discover administrative area columns` |
| 017 | 행정동 코드 정규화 로더 추가 | `src/ktdb/admin_area.py` | 10자리 코드 선행 0 보존 확인 | `feat: load administrative area codes` |
| 018 | 행정동 코드 중복·말소 레코드 정책 추가 | `src/ktdb/admin_area.py` | 코드별 canonical 레코드 수 검사 | `feat: resolve administrative code records` |
| 019 | 행정동 로더 테스트 추가 | `tests/test_admin_area.py` | 중복·말소 fixture 테스트 | `test: validate administrative lookup` |
| 020 | CSV 원본 컬럼 선택 목록 정의 | `src/ktdb/schema.py` | 실제 헤더와 필수 목록 비교 | `feat: define KTDB source columns` |
| 021 | CSV chunk loader 구현 | `src/ktdb/loader.py` | 작은 chunk의 행 수·컬럼 확인 | `feat: add chunked KTDB loader` |
| 022 | 개인·이동 CSV 조인 키 검증 | `src/ktdb/loader.py` | `idx` 중복·누락 진단 출력 | `feat: validate KTDB join keys` |
| 023 | 이동 placeholder 행 필터 규칙 정의 | `src/ktdb/loader.py` | 빈 `TP5_1` 행과 실제 trip 구분 | `feat: identify empty KTDB trip rows` |
| 024 | 원본 행 수 및 진단 요약 생성 | `src/ktdb/diagnostics.py` | raw rows, unique idx/fid 출력 | `feat: add raw dataset diagnostics` |
| 025 | loader 통합 테스트 추가 | `tests/test_loader.py` | fixture 기반 조인·인코딩 테스트 | `test: cover KTDB loading diagnostics` |
| 026 | DATE `MMDD` 파싱 함수 구현 | `src/ktdb/features/time.py` | 2021 날짜와 잘못된 값 테스트 | `feat: parse KTDB survey dates` |
| 027 | 24시 이후 출발시각 정규화 구현 | `src/ktdb/features/time.py` | 24~27시 날짜 rollover 테스트 | `feat: normalize overnight departure times` |
| 028 | weekday 파생 구현 | `src/ktdb/features/time.py` | 날짜별 영문 weekday 확인 | `feat: derive weekday feature` |
| 029 | departure_hour 파생 구현 | `src/ktdb/features/time.py` | 정규화 시간 범위 검사 | `feat: derive departure hour` |
| 030 | departure_minute_bin 상수화 | `src/config.py`, `src/ktdb/features/time.py` | 15분 bin 경계 테스트 | `feat: derive departure minute bins` |
| 031 | time_band 경계 상수화 | `src/config.py`, `src/ktdb/features/time.py` | 모든 시간대 경계 테스트 | `feat: define time band rules` |
| 032 | 시간 Feature 통합 테스트 | `tests/test_time_features.py` | 정상·rollover·결측 케이스 | `test: cover temporal feature engineering` |
| 033 | 원본 장소 코드·이름 컬럼 매핑 정의 | `src/ktdb/features/locations.py` | Code Book 레이블과 일치 확인 | `feat: map KTDB location fields` |
| 034 | 행정동 이름 fallback 결합 구현 | `src/ktdb/features/locations.py` | 누락 이름의 코드 lookup 확인 | `feat: add administrative name fallback` |
| 035 | origin/destination 표준 Feature 생성 | `src/ktdb/features/locations.py` | 6개 공간 Feature 컬럼 검사 | `feat: derive origin destination features` |
| 036 | OD scope 규칙 구현 | `src/ktdb/features/locations.py` | same_dong부터 inter_sido 경계 테스트 | `feat: derive OD scope` |
| 037 | OD Feature 통합 테스트 | `tests/test_location_features.py` | 동일·상이 행정구역 fixture | `test: cover OD feature rules` |
| 038 | 통행목적 코드→label 매핑 구현 | `src/ktdb/features/purpose.py` | TP2 실제 코드북 값 비교 | `feat: map KTDB trip purposes` |
| 039 | 출퇴근 방향 규칙 구현 | `src/ktdb/features/purpose.py` | 집→직장/직장→집만 분류 | `feat: derive commute direction` |
| 040 | commute filtering 구현 | `src/ktdb/features/purpose.py` | non-commute 제외 수 확인 | `feat: filter commute trips` |
| 041 | 목적·출퇴근 테스트 추가 | `tests/test_purpose_features.py` | 코드·OD 조합 경계 테스트 | `test: cover commute classification` |
| 042 | 수단 코드북 사전 추출 로직 구현 | `src/ktdb/features/modes.py` | TP5_1~TP5_10 값 사전 확인 | `feat: load KTDB mode dictionaries` |
| 043 | Canopy 5-class mode mapping 규칙 구현 | `src/config.py`, `src/ktdb/features/modes.py` | walk/bike/car/bus/rail 매핑 확인 | `feat: map KTDB modes to Canopy classes` |
| 044 | 제외 수단 정책 구현 | `src/ktdb/features/modes.py` | airplane/boat/motorcycle/other 진단 | `feat: classify unsupported modes explicitly` |
| 045 | mode mapping 결과표 산출 | `data/processed/.../05_mode_mapping.csv` | raw code·name·class·rule 검사 | `feat: export mode mapping table` |
| 046 | 구간 소요시간 코드북 해석 구현 | `src/ktdb/features/modes.py` | TP5_n_t1 코드 순서와 레이블 확인 | `feat: parse segment duration codes` |
| 047 | multi-modal sequence 생성 구현 | `src/ktdb/features/modes.py` | walk|bus|rail|walk 예제 확인 | `feat: derive multimodal sequences` |
| 048 | longest-duration main mode 선택 구현 | `src/ktdb/features/modes.py` | rail access/egress 예제 테스트 | `feat: select duration-based main mode` |
| 049 | duration tie-break 및 결측 fallback 구현 | `src/ktdb/features/modes.py` | 동률·시간 결측 테스트 | `fix: define main mode tie breaks` |
| 050 | mode parser 통합 테스트 | `tests/test_mode_features.py` | 전체 10구간 fixture | `test: cover multimodal mode parsing` |
| 051 | 좌표 데이터 존재 여부 점검 | `src/ktdb/distance.py`, `reports/` | 원본 파일에 좌표 컬럼 존재 여부 확인 | `docs: assess KTDB coordinate availability` |
| 052 | 좌표가 없을 때 blocker 기록 | `docs/assumptions.md` | 가짜 좌표 미생성 확인 | `docs: record missing coordinate blocker` |
| 053 | Haversine 순수 함수 구현 | `src/common/geo.py` | 서울-부산 등 known distance 테스트 | `feat: add haversine distance function` |
| 054 | 행정동 centroid 입력 스키마 정의 | `schemas/admin_centroid.schema.json` | 필수 코드·lat·lon 검증 | `feat: define centroid input schema` |
| 055 | centroid join을 optional 단계로 구현 | `src/ktdb/distance.py` | 좌표 미제공 시 명시적 skip | `feat: add optional OD distance join` |
| 056 | distance_band 규칙 구현 | `src/ktdb/distance.py` | 0/1/3/5/10/20 경계 테스트 | `feat: derive distance bands` |
| 057 | 거리 결측·매칭률 보고 구현 | `src/ktdb/distance.py` | match rate와 blocker 출력 | `feat: report distance matching coverage` |
| 058 | 거리 테스트 추가 | `tests/test_distance.py` | Haversine·band·결측 테스트 | `test: cover distance features` |
| 059 | Feature schema 문서 작성 | `schemas/ktdb_population_features.schema.json` | 필수·선택 컬럼 검증 | `docs: define KTDB population schema` |
| 060 | Data Dictionary 초안 생성 | `docs/ktdb_data_dictionary.csv` | 원본→최종 컬럼 매핑 검토 | `docs: add KTDB data dictionary` |
| 061 | row-level feature builder 통합 | `src/ktdb/transform.py` | fixture end-to-end 출력 | `feat: integrate KTDB feature builder` |
| 062 | 개인정보·식별자 제외 검증기 구현 | `src/ktdb/validation.py` | 금지 컬럼이 model input에 없는지 확인 | `feat: validate leakage and privacy fields` |
| 063 | 결측치 표준화 정책 구현 | `src/ktdb/validation.py` | categorical sentinel와 numeric 결측 확인 | `feat: standardize feature missing values` |
| 064 | 유효 5-class trip 필터 구현 | `src/ktdb/transform.py` | target class가 5개뿐인지 검사 | `feat: filter valid Canopy trips` |
| 065 | group id 생성 규칙 구현 | `src/ktdb/split.py` | idx 기반 동일 group 확인 | `feat: derive person group identifiers` |
| 066 | deterministic group split 구현 | `src/ktdb/split.py` | group overlap 0 확인 | `feat: add deterministic group split` |
| 067 | split distribution 진단 구현 | `src/ktdb/split.py` | train/validation/test counts 출력 | `feat: report group split distribution` |
| 068 | split 테스트 추가 | `tests/test_split.py` | seed 재현성과 overlap 테스트 | `test: cover leakage safe group split` |
| 069 | all population CSV writer 구현 | `src/ktdb/build_dataset.py` | 재실행 시 동일 checksum 확인 | `feat: write all population dataset` |
| 070 | commute population CSV writer 구현 | `src/ktdb/build_dataset.py` | commute direction만 포함 확인 | `feat: write commute population dataset` |
| 071 | lookup grouping context 정의 | `src/ktdb/lookup.py` | 세부 OD·시간·목적 키 확인 | `feat: define population lookup contexts` |
| 072 | probability normalization 구현 | `src/ktdb/lookup.py` | 5개 확률 합 1 테스트 | `feat: normalize mode probabilities` |
| 073 | minimum sample threshold 설정 | `src/config.py`, `src/ktdb/lookup.py` | threshold 미만 그룹 탐지 | `feat: add lookup sample thresholds` |
| 074 | fallback hierarchy 구현 | `src/ktdb/lookup.py` | 세부→시군구→시도→prior 순서 테스트 | `feat: add lookup fallback hierarchy` |
| 075 | all/commute lookup writer 구현 | `src/ktdb/lookup.py` | 03·04 lookup 컬럼 검사 | `feat: write population baseline lookups` |
| 076 | dataset summary collector 구현 | `src/ktdb/summary.py` | raw/valid/commute/counts 집계 | `feat: collect dataset summary metrics` |
| 077 | missingness와 excluded mode 보고 구현 | `src/ktdb/summary.py` | 결측률·제외수 검증 | `feat: report dataset quality metrics` |
| 078 | build CLI 통합 | `src/build_population_dataset.py` | 단일 명령 clean build 실행 | `feat: add KTDB dataset build CLI` |
| 079 | build pipeline 테스트 | `tests/test_build_pipeline.py` | 작은 fixture 전체 산출물 확인 | `test: cover dataset build pipeline` |
| 080 | CatBoost 학습 입력 모듈 구현 | `src/ktdb/model_data.py` | 금지 컬럼 제외 확인 | `feat: prepare model training inputs` |
| 081 | CatBoost baseline 학습 구현 | `src/train_expected_behaviour.py` | seed·categorical columns 확인 | `feat: train expected behaviour baseline` |
| 082 | class imbalance 진단 및 weight 옵션 추가 | `src/train_expected_behaviour.py` | weight off/on 기록 | `feat: add class imbalance diagnostics` |
| 083 | Accuracy·Macro F1 산출 구현 | `src/train_expected_behaviour.py` | metrics JSON 값 검증 | `feat: report classification metrics` |
| 084 | class precision/recall 산출 구현 | `src/train_expected_behaviour.py` | 5-class report 확인 | `feat: report per-class metrics` |
| 085 | confusion matrix report 구현 | `src/train_expected_behaviour.py` | PNG 생성과 label 순서 확인 | `feat: export confusion matrix report` |
| 086 | model artifact와 metadata 저장 구현 | `src/train_expected_behaviour.py` | `.cbm` reload 테스트 | `feat: persist expected behaviour model` |
| 087 | prediction input validation 구현 | `src/predict_expected_behaviour.py` | 필수 context 누락 오류 확인 | `feat: validate prediction context` |
| 088 | predict_proba API 구현 | `src/predict_expected_behaviour.py` | 확률 합 1과 class order 확인 | `feat: add expected behaviour prediction API` |
| 089 | prediction CLI와 3개 sample 추가 | `src/predict_expected_behaviour.py`, `reports/sample_predictions.json` | 실제 모델 3건 실행 | `feat: add prediction examples` |
| 090 | prediction 테스트 추가 | `tests/test_prediction.py` | probability sum·unknown category 테스트 | `test: cover prediction probabilities` |
| 091 | raw→processed data flow 문서화 | `docs/data_flow.md` | 코드 경로와 문서 일치 확인 | `docs: document KTDB data flow` |
| 092 | assumptions/open questions 문서화 | `docs/assumptions.md` | 거리 blocker와 main-mode rule 확인 | `docs: document KTDB assumptions` |
| 093 | README 실행 명령과 결과 항목 갱신 | `README.md` | clean environment 명령 점검 | `docs: document KTDB pipeline usage` |
| 094 | requirements와 Python 3.11 호환성 점검 | `requirements.txt` | 새 가상환경 설치 테스트 | `chore: pin pipeline dependencies` |
| 095 | sample fixture 정책 추가 | `tests/fixtures/README.md` | 개인정보 없는 fixture 확인 | `test: document safe KTDB fixtures` |
| 096 | 전체 단위 테스트 실행 및 보정 | `tests/` | `pytest` 전체 통과 | `test: stabilize KTDB test suite` |
| 097 | raw manifest와 schema 검증 통합 | `src/validate_dataset.py` | manifest/schema/금지 컬럼 점검 | `feat: add dataset validation CLI` |
| 098 | clean rebuild 스크립트 구현 | `scripts/rebuild_ktdb.ps1` | 임시 산출물 삭제 후 재생성 checksum 비교 | `chore: add clean KTDB rebuild command` |
| 099 | 최종 QA 보고서와 변경 파일 목록 생성 | `reports/final_validation.md` | 요구된 10개 검증 항목 확인 | `docs: add final KTDB validation report` |
| 100 | 처음부터 끝까지 재실행하고 최종 상태 태깅 | `README.md`, `reports/` | raw→prediction 전체 재현·git diff 확인 | `chore: complete KTDB population baseline pipeline` |

## 현재 확인된 조건

- 로컬 원본에는 개인 CSV, 이동 CSV, Code Book, 행정동 코드 workbook이 있다.
- 이동 CSV는 약 191MB이므로 일반 Git 커밋에서 제외한다.
- 행정동 코드 workbook에는 좌표가 확인되지 않았다. 따라서 실제 centroid 데이터가 추가되기 전까지 `od_straight_distance_km`과 `distance_band`는 blocker로 표시하며 임의 좌표를 생성하지 않는다.
- GitHub `origin`과 인증은 별도 단계로 남긴다. GitHub `Verified` 커밋은 로그인만으로 생성되지 않으며, 계정에 연결된 SSH/GPG 서명이 필요하다.
