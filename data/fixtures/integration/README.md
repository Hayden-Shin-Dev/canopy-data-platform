# Integration replay fixtures

각 CSV는 canonical GPS Event Contract를 따르는 입력 fixture입니다. `source`와 파일명은 fixture의 broad behaviour만 설명하며, mode score나 CO2 결과를 하드코딩하지 않습니다.

- `seoul_bus_route.csv`: 서울시 공식 route-stop reference의 서초22 4개 정류장 좌표
- `seoul_subway_line1.csv`: 서울교통공사 1호선 서울역-시청-종각-동대문 좌표
- `seoul_car_no_transit.csv`: transit reference에서 떨어진 서울 이동 경로
- `seoul_walk_bike.csv`: 저속 보행/자전거 후보 경로
- `insufficient_gps.csv`: window를 만들 수 없는 단일 event
- `quality_edge_cases.csv`: 큰 시간 간격, duplicate, out-of-order sequence

fixture는 `python scripts/replay_integration.py <fixture>`로 event-by-event replay합니다.
