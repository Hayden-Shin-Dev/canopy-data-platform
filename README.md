# KTDB SGIS Distance Features

## 이 브랜치의 목적

KTDB 개인통행실태조사 2021의 출발·도착 행정동에 SGIS 2021 대표좌표를 연결하고, 행정동 중심점 사이의 직선거리 Feature를 생성한다.

이 거리는 도로 이동거리가 아니라 Population Baseline에서 사용하는 OD 참고값이다.

## 처리 기준

- KTDB 행정동 코드: 10자리
- SGIS 행정동 코드: 7자리
- 코드가 다르므로 시도·시군구·행정동 전체 이름이 일치하는 경우만 매칭
- SGIS `EPSG:5179` 좌표를 `EPSG:4326`으로 변환한 뒤 Haversine 계산
- Polygon 좌표를 평균내어 대표점을 만들지 않음

거리 구간은 다음과 같다.

`0-2km`, `2-5km`, `5-10km`, `10-20km`, `20km+`

## 실제 결과

- SGIS 읍면동 reference: 3,512개
- Origin 매칭률: 84.81%
- Destination 매칭률: 84.83%
- 거리 계산 성공: 262,432건
- 거리 계산 실패: 68,757건
- 미매칭 행정동: 397개 코드
- 거리 중앙값: 2.641km
- 거리 평균: 7.916km
- 거리 최대: 525.308km

미매칭 목록은 [reports/ktdb_admin_dong_unmatched.csv](reports/ktdb_admin_dong_unmatched.csv)에 기록한다. 미매칭 행정동의 좌표와 거리는 임의로 채우지 않는다.

## 주요 산출물

- [data/reference/admin_dong_centroids_2021.csv](data/reference/admin_dong_centroids_2021.csv): SGIS 대표좌표
- [data/reference/ktdb_sgis_admin_dong_mapping_2021.csv](data/reference/ktdb_sgis_admin_dong_mapping_2021.csv): KTDB-SGIS 매핑 결과
- [reports/ktdb_admin_dong_unmatched.csv](reports/ktdb_admin_dong_unmatched.csv): 미매칭 코드와 건수
- `data/processed/population_baseline/ktdb/01_population_model_training_all.csv`
- `data/processed/population_baseline/ktdb/02_population_model_training_commute.csv`
- `data/processed/population_baseline/ktdb/03_population_lookup_all.csv`
- `data/processed/population_baseline/ktdb/04_population_lookup_commute.csv`
- `data/processed/population_baseline/ktdb/06_dataset_summary.json`

processed CSV와 모델 파일은 용량 때문에 Git에 올리지 않고 로컬에서 재생성한다.

## 실행

프로젝트 루트 `.env`에 키를 입력한다. `.env`는 Git에서 제외된다.

```dotenv
SGIS_CONSUMER_KEY=발급받은 키
SGIS_CONSUMER_SECRET=발급받은 시크릿
```

```powershell
py -3 -m src.build_population_dataset
```

기존 reference를 무시하고 다시 수집하려면 다음 옵션을 추가한다.

```powershell
py -3 -m src.build_population_dataset --refresh-sgis
```

## 검증

`py -3 -m pytest -q` 결과는 125 passed이며, 생성된 전체 Feature CSV는 `src.validate_dataset`에서 331,189행 valid로 확인했다.

현재 브랜치: `dev/ktdb-distance-v1`
