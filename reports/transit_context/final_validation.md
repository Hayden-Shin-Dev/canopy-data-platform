# Transit Context validation

상태: `api_and_reference_validated`

## Reference 결과

- subway_stations: 276 rows, duplicate 0, invalid coordinate 0
- subway_timetable: 424,264 rows, duplicate 496, invalid coordinate None
- korail_stations: 202 rows, duplicate 0, invalid coordinate 0
- subway_station_unmatched: 185 rows, duplicate 0, invalid coordinate None
- seoul_station_lines: 799 rows, duplicate 0, invalid coordinate None
- subway_station_line_enrichment: 273 rows, duplicate 0, invalid coordinate 0
- seoul_station_unmatched: 526 rows, duplicate 0, invalid coordinate None
- Seoul API response: INFO-000
- TAGO live/bus reference response: success

## API 상태

- DATA_GO_KR_SERVICE_KEY: configured
- SEOUL_OPENAPI_KEY: configured
- Seoul API response: INFO-000
- TAGO live/bus reference response: authentication error

## 한계

- Bus references and live positions remain pending because TAGO returned an authentication error.
- Seoul line API response was validated; coordinate coverage remains limited to the supplied 1-8 line file.
- GeoLife is not joined to Korean transit networks.
- Korail source has no line/subtype field; rail subtype remains unknown unless stronger evidence exists.
