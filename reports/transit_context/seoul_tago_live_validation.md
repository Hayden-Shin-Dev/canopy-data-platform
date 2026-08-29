# Seoul TAGO live bus validation

검증일: 2026-08-29

## 조회 대상

- 서울 공식 route-stop reference: `ROUTE_ID=121900014`
- 노선명: `서초22`
- reference 정류장 예시:
  - `NODE_ID=121000081`, 순번 `1`, 남부터미널
  - `NODE_ID=121900230`, 순번 `2`, 남부터미널.기쁨병원
  - `NODE_ID=121900231`, 순번 `3`, 예술의전당
  - `NODE_ID=121900232`, 순번 `4`, 신중초등학교

## TAGO live 조회

Endpoint:

`BusLcInfoInqireService/getRouteAcctoBusLcList`

요청 조건:

- `cityCode=11` (서울로 확인되는 코드로 조회)
- `routeId=121900014`
- `pageNo=1`, `numOfRows=10`, `_type=json`

응답:

```json
{
  "resultCode": "00",
  "resultMsg": "NORMAL SERVICE.",
  "totalCount": 0,
  "items": ""
}
```

TAGO `getCtyCodeList` 응답은 138개 도시를 반환했지만 `citycode=11` 또는
`11000` 항목은 포함하지 않았습니다. 따라서 이번 조회에는 TAGO
`routeId`, `nodeId` 또는 `nodeord`가 존재하지 않았고, 서울 reference의
`ROUTE_ID`/`NODE_ID`와 연결할 실제 live 행도 없었습니다.

## 판정

**NOT CONNECTED**

공식 ID 기반 연결 PASS가 아닙니다. 좌표와 순번 reference는 서울 공식
파일로 검증되었지만, 현재 승인된 TAGO BusLcInfoInqireService가 서울
실시간 노선 데이터를 제공하지 않으므로 live bus-position evidence는
서울 POC의 미지원 한계로 남깁니다. 빈 응답을 정류장이나 차량으로
추정하지 않았습니다.

원본 응답은 로컬 캐시
`data/cache/transit/tago_seoul_live_route_121900014.json`에 저장되며,
API 키는 포함하지 않습니다.
