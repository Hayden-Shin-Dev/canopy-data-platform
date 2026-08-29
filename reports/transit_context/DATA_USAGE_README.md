# Transit Context 데이터 사용 안내

이 문서는 현재 서울 POC에서 실제로 사용하는 reference와, 조사 과정에서
확인했지만 최종 runtime에는 연결하지 않는 자료를 구분합니다.

## 최종 ACTIVE 데이터

| 구분 | 데이터 | 생성/입력 파일 | 실제 사용 기능 |
| --- | --- | --- | --- |
| Bus | 서울시 공식 노선별 정류소 정보 | `data/raw/transit/서울시버스노선별정류소정보_20260804.xlsx` | `seoul_bus_stops.csv`, `seoul_bus_route_stops.csv`, Bus Context 공간·노선·순번 evidence |
| Subway | 서울교통공사 1~8호선 역사 좌표 | `data/raw/transit/서울교통공사_1_8호선 역사 좌표(위경도) 정보_20250814.csv` | 역 proximity |
| Subway | 서울교통공사 열차운행시각표 | `data/raw/transit/서울교통공사_서울 도시철도 열차운행시각표_20260616.csv` | timetable compatibility reference |
| Subway | 서울 지하철 station-line API 결과 | `seoul_station_lines.csv`, `subway_station_line_enrichment.csv` | station-line evidence |
| Train | 한국철도공사 역 위치 정보 | `data/raw/transit/한국철도공사_역 위치 정보_20240401.csv` | KORAIL station proximity / train context |
| Runtime | Transit 설정·evidence·resolver | `config/transit_context.json`, `src/transit_context/` | GPS endpoint context와 최종 mode 결정 |

서울 Bus reference는 하나의 공식 파일 안에서 `ROUTE_ID`와 `NODE_ID`를
사용합니다. 718개 노선, 12,898개 정류장, 41,676개 route-stop 행 모두
유효한 좌표를 갖습니다.

## OPTIONAL / LEGACY 데이터

| 구분 | 데이터 | 이유 |
| --- | --- | --- |
| LEGACY | TAGO `BusStop/getBusStop` | 서울 POC와 ID 체계가 연결되지 않음 |
| LEGACY | TAGO `BusRoutespecificStopInformation` | 서울 공식 route-stop reference의 runtime 입력이 아님 |
| LEGACY | 국토교통부 전국 버스정류장 위치정보 파일 | TAGO ID와 exact match가 0건이고 서울 POC 범위 밖 |
| OPTIONAL | TAGO `BusLcInfoInqireService` | 서울 도시코드/노선 live 행이 없어 현재 runtime dependency로 사용하지 않음 |

위 자료는 조사·검증 기록과 향후 전국 확장 검토를 위해 보존하지만,
현재 서울 POC의 Bus Context가 참조하는 데이터는 아닙니다. API key와
원본 대용량 파일은 Git에 커밋하지 않습니다.

## 재생성 명령

```powershell
python scripts/build_transit_references.py `
  --subway-coordinates data/raw/transit/서울교통공사_1_8호선 역사 좌표(위경도) 정보_20250814.csv `
  --subway-timetable data/raw/transit/서울교통공사_서울 도시철도 열차운행시각표_20260616.csv `
  --korail-stations data/raw/transit/한국철도공사_역 위치 정보_20240401.csv

python scripts/build_seoul_bus_reference.py `
  data/raw/transit/서울시버스노선별정류소정보_20260804.xlsx
```
