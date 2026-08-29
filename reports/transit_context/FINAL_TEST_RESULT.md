# Transit Context 최종 테스트 결과

## Bus

- 결과: PASS
- 사용 데이터: 서울시 공식 노선별 정류소 정보 workbook
- 실제 fixture: `tests/fixtures/seoul_bus_route_fixture.csv`
- 노선: `ROUTE_ID=121900014` (서초22)
- 검증 흐름: GPS endpoint → nearby stops → route candidate → `NODE_ID`/순번 → Bus Context → Resolver
- 결과: route ID `121900014`, sequence score `1.0`, Bus Context score `0.70`, final mode `bus`
- 전체 reference: 718 routes, 12,898 stops, 41,676 route-stop rows, coordinate coverage 100%

## Subway

- 결과: PASS
- 사용 데이터: 서울교통공사 역사 좌표·열차운행시각표와 서울 station-line API 결과
- 실제 endpoint pair: 1호선 역 ID `159`(동묘앞) → `157`(제기동)
- 결과: 동일 line `1`, endpoint proximity, timetable compatibility 확인

## KORAIL

- 결과: PASS
- 사용 데이터: 한국철도공사 역 위치 정보
- 실제 endpoint pair: `korail:서울` → `korail:용산`
- 결과: 두 역 proximity와 train context score 계산 확인

## Resolver

- 결과: PASS
- 근거: `tests/test_transit_resolver.py`, `tests/test_transit_synthetic_cases.py`, 서울 Bus integration test

## 전체 pytest

- 결과: PASS
- 실행: `python -m pytest -q`
- 결과: `169 passed, 20 warnings`
- warnings는 외부 joblib deprecation과 sklearn 단일 label 경고이며 테스트 실패는 아닙니다.

## API와 데이터 검증

- 서울 station-line API: `INFO-000`
- TAGO probe: 응답 가능 여부만 확인
- TAGO 서울 live route 조회: `NOT CONNECTED` (`totalCount=0`)
- TAGO live와 전국 정류장 파일은 서울 POC runtime dependency에서 제외

## 최종 판정

서울 공식 reference 기반 Bus/Subway/KORAIL POC와 전체 테스트는 PASS입니다.
전국 TAGO 매칭과 TAGO 서울 live bus evidence는 POC 범위 밖이며,
이를 이유로 전국 지원이나 실시간 bus 연결을 주장하지 않습니다.
