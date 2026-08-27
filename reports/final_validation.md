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

## 남은 데이터 blocker

현재 KTDB 제공 파일에는 행정동 대표 좌표가 없어 OD 직선거리와 distance band를
계산하지 않았다. 좌표 파일이 준비되면 `scripts/rebuild_ktdb.ps1`에
`--centroid-file`을 전달해 같은 pipeline으로 재생성한다.
