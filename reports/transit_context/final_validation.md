# Transit Context validation

상태: `INCOMPLETE_PENDING_FINAL_CHECKLIST`

## Reference 결과

- subway_stations: 276 rows, duplicate 0, invalid coordinate 0
- subway_timetable: 424,264 rows, duplicate 496, invalid coordinate None
- korail_stations: 202 rows, duplicate 0, invalid coordinate 0
- subway_station_unmatched: 185 rows, duplicate 0, invalid coordinate None
- bus_stops: 31 rows, duplicate 0, invalid coordinate 0
- bus_route_stops: 130 rows, duplicate 0, invalid coordinate 0
- bus_stop_unmatched: 346 rows, duplicate 0, invalid coordinate 346
- bus_route_stop_unmatched: 1,715 rows, duplicate 0, invalid coordinate 1715
- seoul_bus_stops: 12,898 rows, duplicate 0, invalid coordinate 0
- seoul_bus_route_stops: 41,676 rows, duplicate 0, invalid coordinate 0
- seoul_station_lines: 799 rows, duplicate 0, invalid coordinate None
- subway_station_line_enrichment: 273 rows, duplicate 0, invalid coordinate 0
- seoul_station_unmatched: 526 rows, duplicate 0, invalid coordinate None
- Seoul API response: INFO-000
- TAGO live/bus reference response: success
- BusStop API rows: 377
- National location file rows: 227,065
- Exact ID matches: 0
- Name/region matches: 31
- Unmatched stops: 346
- Stop coordinate match rate: 8.223%
- Route rows with coordinates: 130
- Route rows without coordinates: 1,715
- Seoul bus total stops: 12,898
- Seoul bus coordinate stops: 12,898
- Seoul bus coordinate coverage: 100.000%
- Seoul bus routes: 718
- Seoul route-stop rows: 41,676
- Seoul route-stop coordinate coverage: 100.000%
- Seoul invalid coordinate rows: 0
- Seoul duplicate route-stop rows removed: 0

## API 상태

- DATA_GO_KR_SERVICE_KEY: configured
- SEOUL_OPENAPI_KEY: configured
- Seoul API response: INFO-000
- TAGO live/bus reference response: success

## 한계

- TAGO references are currently limited to the requested 광주 서구 sample scope.
- TAGO BusStop and route-stop responses do not provide latitude/longitude; matched coordinates come only from the supplied national bus stop file.
- Seoul line API response was validated; coordinate coverage remains limited to the supplied 1-8 line file.
- GeoLife is not joined to Korean transit networks.
- Korail source has no line/subtype field; rail subtype remains unknown unless stronger evidence exists.
