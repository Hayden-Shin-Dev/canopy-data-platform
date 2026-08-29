# Transit Context

## 목적

Transit Context는 GeoLife나 iOS GPS의 ML 예측을 대체하지 않고, 실제 대중교통 네트워크와 시간 정보를 근거로 bus·subway·train 판단을 보조하는 evidence layer입니다.

## Reference

- 서울교통공사 1~8호선 역사 좌표
- 서울교통공사 도시철도 운행시각표
- 한국철도공사 역 위치
- 버스 정류장·노선 데이터는 TAGO API 연동 후 생성

정규화 결과는 `data/processed/transit_context/`에 생성합니다. 원본 CSV는 `data/raw/transit/`에 보관하며 수정하거나 Git에 커밋하지 않습니다.

## 판단 흐름

GPS Window → 정류장·역 근접성 → route/line·순서·시간표 증거 → multi-window Trip Context → ML 확률과 보수적 결합

단일 정류장 근접성만으로 bus나 rail을 확정하지 않습니다. GeoLife는 한국 transit network와 결합하지 않으며, 코레일 파일에 없는 철도 노선·subtype도 추측하지 않습니다.

## 현재 결과

- subway_stations.csv: 276 rows
- subway_timetable.csv: 424,264 rows
- korail_stations.csv: 202 rows
- subway station unmatched keys: 185
- bus_stops.csv: 377 rows (광주 서구 샘플, API 좌표 미제공)
- bus_route_stops.csv: 1,845 rows (광주 서구 샘플, API 좌표 미제공)
- Seoul station-line API: `INFO-000`, 799 rows
- TAGO bus APIs: all three endpoints respond successfully; BusStop/route responses contain no latitude/longitude

## Bus coordinate matching

TAGO BusStop와 BusRoutespecificStopInformation 응답을 국토교통부 전국 버스정류장 위치정보 파일과 결합합니다. 정류장번호 exact match를 먼저 시도하고, 지역명이 확인된 뒤 유일한 정류장명+지역 match만 좌표를 붙입니다. 중복 후보는 추측하지 않고 unmatched 파일에 남깁니다.

- 전국 위치정보 파일: 227,065 rows
- BusStop API sample: 377 rows
- exact ID match: 0 rows
- name/region exact match: 31 rows
- 좌표가 있는 bus_stops.csv: 31 rows
- 좌표가 있는 bus_route_stops.csv: 130 rows
- 결과 요약: `data/processed/transit_context/bus_match_summary.json`

## 실행

```powershell
python scripts/build_transit_references.py `
  --subway-coordinates data/raw/transit/서울교통공사_1_8호선 역사 좌표(위경도) 정보_20250814.csv `
  --subway-timetable data/raw/transit/서울교통공사_서울 도시철도 열차운행시각표_20260616.csv `
  --korail-stations data/raw/transit/한국철도공사_역 위치 정보_20240401.csv

python scripts/validate_transit_context.py
python scripts/fetch_seoul_reference.py --refresh-seoul
python scripts/fetch_tago_reference.py --refresh-tago
```

전국 정류장 파일을 명시하려면 다음 옵션을 추가합니다.

```powershell
python scripts/fetch_tago_reference.py --refresh-tago `
  --national-bus-stops data/raw/transit/국토교통부_전국 버스정류장 위치정보_20251031.csv
```

`reports/transit_context/final_validation.md`와 `validation.json`에 실제 처리 수치와 미검증 항목을 기록합니다.
