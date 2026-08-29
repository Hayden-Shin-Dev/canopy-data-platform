# KTDB Population Baseline v1 검증 기록

## 코드 검증

- `python -m pytest -q` 결과: 39 passed
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

`src.build_population_dataset`는 SGIS 2021 행정동 reference가 없을 때 환경변수
`SGIS_CONSUMER_KEY`와 `SGIS_CONSUMER_SECRET`로 계층 수집한다. 수집 결과는
`data/reference/admin_dong_centroids_2021.csv`에 cache하고, `--refresh-sgis`로
강제 갱신한다. SGIS 10자리/7자리 코드 차이는 전체 행정구역명 exact match로
검증하며, 임의의 코드 자르기나 Polygon 평균은 사용하지 않는다.

재빌드 후 `06_dataset_summary.json`에는 SGIS 행정동 수, 출발·도착 매칭률,
거리 성공·실패 행 수, 거리 통계, distance band별 건수와 미매칭 리포트 경로가
기록된다. 현재 작업 환경에는 SGIS 자격 증명이 없어 전국 reference와 실제
거리 수치는 아직 생성하지 않았다.
