# Transit Context validation

상태: `reference_only_api_pending`

## Reference 결과

- subway_stations: 276 rows, duplicate 0, invalid coordinate 0
- subway_timetable: 424,264 rows, duplicate 496, invalid coordinate None
- korail_stations: 202 rows, duplicate 0, invalid coordinate 0
- subway_station_unmatched: 185 rows, duplicate 0, invalid coordinate None

## API 상태

- DATA_GO_KR_SERVICE_KEY: API key unavailable
- SEOUL_OPENAPI_KEY: API key unavailable
- 실제 API 호출: 없음

## 한계

- Bus references and live positions were not fetched without DATA_GO_KR_SERVICE_KEY.
- Seoul line API enrichment was not fetched without SEOUL_OPENAPI_KEY.
- GeoLife is not joined to Korean transit networks.
- Korail source has no line/subtype field; rail subtype remains unknown unless stronger evidence exists.
