# KTDB Population Baseline 가정과 blocker

- `TP2`, `TP5_*`, 시간·지역 컬럼의 의미는 원본 Code book을 기준으로 해석한다.
- `actual_mode`는 walk, bike, car, bus, rail 다섯 class만 사용한다. 지원하지 않는
  수단은 유효 학습 행에서 제외하고 mode mapping에 원시 코드를 남긴다.
- 사람별 `person_group_id`로 train/validation/test를 나눠 동일 응답자의 이동이
  평가 집합으로 새지 않게 한다.
- 현재 제공된 KTDB 파일에는 행정동 좌표가 없다. 따라서 행정동 중심점 간
  `od_straight_distance_km`와 `distance_band`는 값을 만들지 않고 결측으로 둔다.
  좌표 원본이 추가되면 `--centroid-file`로 연결한다.
- 중심점 직선거리는 실제 도로 이동거리와 다르며, 서비스 경로 거리는 향후 GPS와
  Azure Maps 데이터로 별도 계산한다.
