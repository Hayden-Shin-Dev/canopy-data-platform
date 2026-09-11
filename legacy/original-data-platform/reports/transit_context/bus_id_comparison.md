# Bus identifier comparison

현재 TAGO 샘플과 전국 정류장 파일은 같은 ID를 사용하지 않습니다. 아래 값은 2025-08-01 광주 서구 TAGO 응답과 2025-10-31 국토교통부 파일을 그대로 읽어 비교한 예시입니다.

| source | stop ID | BIMS/ARS ID | stop name | region | coordinate |
| --- | --- | --- | --- | --- | --- |
| TAGO BusStop | `00000011` | `sttn_ars_no=~` | `5.18기념문화센터` | `ctpv_cd=29`, `sgg_cd=29140`, `emd_cd=2914011800` | not provided |
| TAGO route-stop | `00001802` | route `00000001`, sequence `2` | `서창농협벽진지점` | `광주광역시`, `서구` | not provided |
| national location file | `ADB354000001` | mobile `540001` | `길안정류장` | city `37040`, `경상북도 안동시` | `36.458658, 128.891228` |
| national location file | `KJB3908` | mobile `1130` | `문화전당역` | city `24`, `광주광역시` | `35.14624502, 126.9189595` |

The observed exact intersections were zero for both national `정류장번호` and
`모바일단축번호`. TAGO region code `29` was linked to national city code `24`
only because both responses explicitly identified `광주광역시`; this is a
documented code-system mapping, not a numeric substring conversion. The
remaining name candidates were often duplicated, so they remain unmatched.

For the Seoul POC, the official Seoul route-stop workbook is preferable: it
contains `ROUTE_ID`, `NODE_ID`, route name, stop sequence, stop name and X/Y in
the same record. The Seoul builder therefore joins by exact `NODE_ID` inside
that source and does not use fuzzy matching.
