# KTDB Population Baseline v1 검증 기록

## 코드 검증

- `py -3 -m pytest -q` 결과: 125 passed, 20 warnings
- 모든 새 커밋은 SSH signing을 사용했고 GitHub API의 `verification.verified`가 true임.
- `data/raw/ktdb/` 원본 파일은 처리 과정에서 수정하지 않음.
- 생성 CSV에는 사람 단위 group split을 적용하고, 모델 입력에서는 식별자와 원시 응답 코드를 제외함.

## 원본 smoke build 기준

- raw trip rows: 356,899
- valid feature rows: 331,189
- commute rows: 86,561
- excluded rows: 25,710
- mode class: walk 98,467 / bike 4,679 / car 172,593 / bus 33,068 / rail 22,382
- split: train 232,489 / validation 49,396 / test 49,304

## SGIS 거리 Feature 재현 경로

`src.build_population_dataset`는 SGIS 2021 행정동 reference를 환경변수 또는
프로젝트 루트 `.env`의 `SGIS_CONSUMER_KEY`, `SGIS_CONSUMER_SECRET`로 수집한다.
수집 결과는 `data/reference/admin_dong_centroids_2021.csv`에 cache하고,
`--refresh-sgis`로 강제 갱신한다. SGIS 10자리/7자리 코드 차이는 전체 행정구역명
exact match로 검증하며, 임의의 코드 자르기나 Polygon 평균은 사용하지 않는다.

실제 재빌드 결과는 다음과 같다.

- SGIS 읍면동: 3,512개
- KTDB origin 매칭률: 84.81%
- KTDB destination 매칭률: 84.83%
- 거리 계산 성공/실패: 262,432 / 68,757건
- 거리 최소/중앙값/평균/최대: 0.000 / 2.641 / 7.916 / 525.308km
- distance band: `0-2km` 118,244 / `2-5km` 47,910 / `5-10km` 42,196 /
  `10-20km` 30,068 / `20km+` 24,014건
- 미매칭 행정동: 397개 코드(출발·도착별 794행), 상세는
  `reports/ktdb_admin_dong_unmatched.csv`

전체 원본 행과 생성 CSV는 Git에 올리지 않고, 실행 결과 요약은 로컬
`data/processed/population_baseline/ktdb/06_dataset_summary.json`에 기록한다.
