# Transit Context

서울 POC에서 GPS 이동을 Bus, Subway, Train Context와 비교해 ML mode 판단을 보조하는 evidence layer입니다.

## 현재 상태

**COMPLETE (SEOUL POC)**

- Bus: 서울 공식 노선별 정류소 reference
- Subway: 역사 좌표, station-line, timetable
- Train: KORAIL 역 좌표
- 전체 테스트: 169 passed

## ACTIVE reference

- `seoul_bus_stops.csv`: 12,898개 정류장 좌표
- `seoul_bus_route_stops.csv`: 41,676개 노선-정류장 행, 718개 노선
- `subway_station_line_enrichment.csv`: 서울 station-line 연결 결과
- `subway_timetable.csv`: 열차운행시각표
- `korail_stations.csv`: KORAIL 역 좌표

버스 POC는 서울시 공식 노선별 정류소 파일의 `ROUTE_ID`, `NODE_ID`,
정류장 순번, 정류장명, X/Y를 그대로 사용합니다. 모든 버스 정류장과
route-stop 행의 좌표 coverage는 100%이며, fuzzy matching을 사용하지 않습니다.

## POC 검증

실제 서울 노선 `121900014`의 정류장 4개를 사용한 Bus Context integration,
1호선 역 endpoint와 timetable 확인, KORAIL 서울–용산 endpoint를 검증했습니다.

- [DATA_USAGE_README.md](reports/transit_context/DATA_USAGE_README.md)
- [FINAL_TEST_RESULT.md](reports/transit_context/FINAL_TEST_RESULT.md)
- [FINAL_CHECKLIST.md](reports/transit_context/FINAL_CHECKLIST.md)

## POC 범위 밖

TAGO BusStop/BusRoutespecificStopInformation과 전국 정류장 파일 매칭,
TAGO 서울 live bus-position evidence, 전국 버스 coverage는 LEGACY 또는
OPTIONAL 확장 과제입니다. 현재 서울 POC runtime dependency가 아닙니다.

## 재생성

```powershell
python scripts/build_transit_references.py `
  --subway-coordinates data/raw/transit/서울교통공사_1_8호선 역사 좌표(위경도) 정보_20250814.csv `
  --subway-timetable data/raw/transit/서울교통공사_서울 도시철도 열차운행시각표_20260616.csv `
  --korail-stations data/raw/transit/한국철도공사_역 위치 정보_20240401.csv

python scripts/build_seoul_bus_reference.py `
  data/raw/transit/서울시버스노선별정류소정보_20260804.xlsx

python -m pytest -q
```
