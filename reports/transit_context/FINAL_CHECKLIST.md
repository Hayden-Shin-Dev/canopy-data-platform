# Transit Context final checklist

현재 전체 상태: **INCOMPLETE**

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 서울 버스 reference coverage 확보 | PASS | `seoul_bus_match_summary.json`: 12,898/12,898 stops with coordinates (100%) |
| 서울 route-stop-coordinate 연결 | PASS | `seoul_bus_match_summary.json`: 41,676/41,676 rows (100%) |
| TAGO 전국 버스 coverage | FAIL | 현재 TAGO 샘플은 광주 서구이며 377건 중 31건만 좌표 연결 (`bus_match_summary.json`) |
| Bus Context 실제 reference integration | PASS | `tests/test_transit_reference_integration.py` |
| Subway 실제 reference integration | PASS | `tests/test_rail_reference_integration.py::test_real_seoul_subway_line_one_endpoint_pair` |
| KORAIL 실제 reference integration | PASS | `tests/test_rail_reference_integration.py::test_real_korail_seoul_yongsan_endpoint_pair` |
| Resolver synthetic tests | PASS | `tests/test_transit_resolver.py`, `tests/test_transit_synthetic_cases.py` |
| API validation | PASS | `reports/transit_context/validation.json`: Seoul `INFO-000`, TAGO probes `success` |
| 데이터 validation | PASS | `reports/transit_context/final_validation.md` |
| 전체 관련 테스트 | PASS | `pytest -q`: 169 passed, 20 warnings |
| 최종 상태와 실제 결과 일치 | PASS | `validation.json` status=`INCOMPLETE_PENDING_FINAL_CHECKLIST`, completion=`INCOMPLETE` |

TAGO 전국 샘플 연결은 POC 수준으로 별도 유지합니다. `bus_id_comparison.md`에
실제 ID·지역·정류장명 비교와 exact match 0건의 원인을 기록했습니다.

이 표에 FAIL 또는 NOT TESTED가 남아 있으므로 `Transit Context COMPLETE`로
표시하지 않습니다.
