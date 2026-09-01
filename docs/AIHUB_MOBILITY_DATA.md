# AI-Hub 교통수단 판별 데이터 조사

조사일: 2026-09-01
조사 브랜치: `research/aihub-mobility-data`
조사 기준 커밋: `9be8b21` (`evaluation/seoul-synthetic-v3-baseline`)

## 이번 문서의 범위

이번 단계에서는 데이터를 실제로 학습시키거나 Production 코드를 바꾸지 않고, 새로 받은 AI-Hub 데이터의 구조와 사용 가능성만 확인했다. 원본은 Canopy 저장소로 복사하지 않았고, 아래 로컬 경로를 읽기 전용으로 조사했다.

```text
C:\Users\user\Downloads\186.교통수단판별 데이터\01-1.정식개방데이터
```

Production Movement ML, 기존 model artifact, Temporal Decoder, Transit Context, frozen `evaluation_dataset_v3`, `main`은 변경하지 않았다.

## 폴더 구조

```text
01-1.정식개방데이터/
├─ Training/
│  ├─ 01.원천데이터/
│  │  ├─ TS_교통수단판별_3.GPS_01.WALK/
│  │  ├─ TS_교통수단판별_3.GPS_02.BIKE/
│  │  ├─ TS_교통수단판별_3.GPS_03.CAR/
│  │  ├─ TS_교통수단판별_3.GPS_04.BUS/
│  │  ├─ TS_교통수단판별_3.GPS_05.SUBWAY/
│  │  └─ TS_OD(종단간)통행궤적/
│  └─ 02.라벨링데이터/
│     ├─ TL_교통수단판별_1.WALK/
│     ├─ TL_교통수단판별_2.BIKE/
│     ├─ TL_교통수단판별_3.CAR/
│     ├─ TL_교통수단판별_4.BUS/
│     ├─ TL_교통수단판별_5.SUBWAY/
│     └─ TL_OD(종단간)통행궤적/
├─ Validation/
│  ├─ 01.원천데이터/ (Training과 같은 5개 GPS class와 OD)
│  └─ 02.라벨링데이터/ (Training과 같은 5개 GPS class와 OD)
└─ Other/
   ├─ 01.연계데이터_003.차량이동궤적_2/
   └─ 01.연계데이터_004.대중교통궤적/
```

`Other`는 차량·대중교통 연계 데이터가 별도로 들어 있는 폴더다. 이번 단계에서는 파일 구조만 확인했고 학습이나 평가에는 사용하지 않았다.

## 파일 규모

아래 수치는 디렉터리의 실제 파일을 세어 계산한 값이다. GPS 파일 수는 곧 class별 trajectory 수로 볼 수 있지만, 파일 안의 GPS point 총합은 이번 조사에서 전체를 다시 읽지 않았다.

| 구분 | WALK | BIKE | CAR | BUS | SUBWAY | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| Training GPS 원천 | 14,916 | 3,476 | 30,824 | 19,884 | 26,848 | 95,948 |
| Training GPS Label | 14,916 | 3,476 | 30,824 | 19,884 | 26,848 | 95,948 |
| Validation GPS 원천 | 1,864 | 434 | 3,853 | 2,485 | 3,356 | 11,992 |
| Validation GPS Label | 1,864 | 434 | 3,853 | 2,485 | 3,356 | 11,992 |

Training GPS class 비율은 WALK 15.55%, BIKE 3.62%, CAR 32.13%, BUS 20.72%, SUBWAY 27.98%다. BIKE가 가장 적지만, 단순 class 비율만으로 학습 가능 여부를 결정하지 않고 사용자 단위 분할과 point 품질을 함께 봐야 한다.

OD 파일은 Training 원천 150,976개와 Label 150,976개, Validation 원천 16,257개와 Label 16,257개다. 파일명 stem을 기준으로 확인한 결과 네 구간 모두 원천과 Label의 누락·초과가 0개였다.

## GPS와 Label schema

대표 GPS 파일의 실제 header는 다음과 같다.

```text
timestamp,accuracy,latitude,longitude,altitude
```

대표 Label 파일의 실제 header는 다음과 같다.

```text
timestamp,label,detail_label
```

GPS 파일명은 다음 패턴이다.

```text
TMC-GPS-{첫 번째 식별자}-{문자열}-{문자열}-Dataset.csv
```

Label 파일은 같은 이름에서 `TMC-GPS`가 `TMC-LABEL`로, `Dataset.csv`가 `Label.csv`로 바뀐다. Training과 Validation의 다섯 class에서 파일명 변환으로 1:1 연결을 확인했다. 각 split·class별 100개 파일을 읽어 GPS와 Label의 timestamp 순서를 비교했으며, 1,000개 표본 모두 불일치가 없었고 파일별 행 수 중앙값도 양쪽 모두 60개였다.

파일명 첫 번째 식별자 기준으로 UID 후보를 세었다. 나머지 두 문자열은 파일명에는 들어 있지만, 이 문서에서 SID·TID라고 임의로 해석하지 않는다. UID/TID/SID의 공식 의미는 AI-Hub 제공 설명서와 metadata를 추가로 확인한 뒤에만 코드에서 이름을 확정해야 한다.

timestamp는 대표 파일에서 13자리 Unix millisecond 값이었다. 20개 파일씩 표본 조사한 sampling interval은 모두 1,000ms였다. 다만 모든 파일이 항상 1초 간격이라고 확정한 것은 아니며, 전체 분포는 ingestion 단계에서 다시 계산해야 한다.

## Label 값과 Canopy class

디렉터리 이름은 WALK, BIKE, CAR, BUS, SUBWAY로 나뉜다. 표본 Label을 확인했을 때 다음 값이 관찰됐다.

| 디렉터리 class | 표본에서 관찰한 `label` | 표본에서 관찰한 `detail_label` |
|---|---:|---:|
| WALK | 0 | 2 |
| BIKE | 1 | 4 |
| CAR | 2 | 5, 12 |
| BUS | 3 | 6 |
| SUBWAY | 5 | 8 |

이는 표본 관찰값이며, 숫자 코드의 공식 의미를 대신하지 않는다. Canopy 최종 class에는 SUBWAY를 RAIL로 연결할 계획이지만, 실제 ingestion 코드에서는 공식 codebook 확인 후 명시적인 mapping table로 관리해야 한다. 숫자 4가 비어 있다는 사실만으로 다른 의미를 추측하지 않는다.

## OD schema

대표 OD 원천 파일의 header는 다음과 같다.

```text
timestamp,latitude,longitude
```

대표 OD Label은 JSON이며, 최상위에서 `move_purpose`, `gender`, `age`, `stime`, `etime`, `trspt` 키를 확인했다. `stime`, `etime`, `trspt`의 각 항목에는 `odid`, `tid`, `value`가 들어 있다. 표본 500개에서 `trspt` 값은 0, 1, 2, 3, 5, 6이 관찰됐고, 여러 segment를 가진 파일은 185개, 최대 9 segment였다. 이 숫자도 공식 교통수단 mapping을 확정하는 근거로 사용하지 않는다.

OD 원천과 Label은 `UT-...-Dataset.csv`와 같은 stem의 `UT-...-Label.json`으로 연결된다. Training과 Validation 모두 파일명 기준 누락·초과가 0개였다.

## 품질 확인 결과

- GPS class별 원천과 Label 파일 수가 모두 일치했다.
- 표본 1,000개 파일에서 GPS·Label timestamp 순서 불일치가 없었다.
- 표본 GPS 좌표는 위도·경도 범위 안에 있었다.
- 표본에서 빈 좌표·accuracy·altitude 행이 관찰됐다. 예를 들어 BUS 표본 파일에는 timestamp는 있지만 accuracy, latitude, longitude, altitude가 모두 빈 행이 연속으로 있었다. 따라서 ingestion 시 좌표 필수값 검증과 결측 행 처리 규칙이 필요하다.
- 표본 20개씩의 파일 길이는 모두 60행이었지만, 전체 trajectory 길이의 최소·최대·중앙값은 아직 계산하지 않았다.
- 전체 GPS point 수, 전체 sampling gap 분포, 중복 point, 역순 timestamp, 비정상 gap, 좌표 결측률은 ingestion profiling 단계에서 streaming 방식으로 계산해야 한다.

### 사용자 분할 누수

파일명 첫 번째 식별자를 UID 후보로 사용해 계산한 결과는 다음과 같다.

| 구분 | UID 수 |
|---|---:|
| Training | 1,095 |
| Validation | 846 |
| 두 split의 공통 UID | 846 |

Validation UID 846명이 모두 Training에도 존재한다. 따라서 제공된 Training/Validation을 그대로 모델 선택이나 최종 성능 보고에 사용하면 사용자 단위 leakage가 생긴다. 이후 ingestion 단계에서 공식 UID 의미를 확인한 뒤, 동일 사용자가 한 split에만 들어가도록 Group Split을 새로 만들어야 한다. 현재 Validation은 독립 검증 세트로 간주하지 않는다.

## Canopy에서의 사용 가능성

이 데이터는 위도·경도·timestamp·accuracy·altitude와 운송수단 Label을 함께 제공하므로, iPhone GPS와 공통으로 계산할 수 있는 속도·방향·정지·간격 기반 feature를 만들 수 있는 후보 데이터다. GeoLife에 비해 원천 column이 단순하므로 speed와 heading은 좌표와 시간으로 다시 계산해야 하고, accuracy 결측 처리도 필요하다.

다만 지금 바로 Production에 넣을 수 있는 상태는 아니다.

1. 공식 codebook을 확보해 UID/TID/SID와 Label 숫자 코드의 의미를 확정해야 한다.
2. UID overlap을 제거한 사용자 독립 Group Split을 먼저 만들어야 한다.
3. 전체 point-level 품질 통계를 streaming으로 계산해야 한다.
4. AI-Hub only와 GeoLife+AI-Hub를 같은 독립 한국 검증 기준으로 비교해야 한다.
5. SUBWAY를 Canopy RAIL로 바꾸는 mapping은 위 검증과 함께 명시적으로 버전 관리해야 한다.

따라서 GeoLife를 지금 제거하거나, AI-Hub가 자동으로 더 좋은 데이터라고 가정하지 않는다. 두 데이터의 domain 차이와 사용자 독립 검증 결과를 본 뒤 Production 학습 구성을 결정한다.

## 다음 구현 순서

1. 공식 AI-Hub codebook과 metadata를 보관하고 식별자 의미를 고정한다.
2. AI-Hub 원본을 수정하지 않는 streaming inventory를 만든다.
3. GPS 파일과 Label 파일을 schema·timestamp·좌표 규칙으로 연결한다.
4. UID 기준 Group Split을 생성하고 split manifest를 저장한다.
5. 공통 GPS feature extraction adapter와 결측·gap 처리 테스트를 추가한다.
6. AI-Hub only 후보를 학습하고 validation에서 class별 지표와 confusion matrix를 기록한다.
7. GeoLife+AI-Hub 후보를 같은 split 원칙으로 비교한다.
8. OD의 공식 `trspt` mapping과 segment timestamp를 검증한 뒤 Temporal Decoder 활용 가능성을 별도 실험한다.
9. 검증이 통과한 후보만 frozen `evaluation_dataset_v3`에서 마지막 한 번 평가한다.
10. Production 반영 여부는 독립 검증 결과와 회귀 테스트를 확인한 뒤 별도 릴리스 작업으로 결정한다.

이번 단계에서는 위 계획의 1단계 전 조사만 수행했다. 모델 학습, artifact 교체, pipeline 수정, v3 실행, main merge, tag 생성은 하지 않는다.
