# Candidate hypotheses

## Candidate A — endpoint route consistency

정류장 후보가 시작점과 끝점 모두에서 같은 route에 속할 때만 route score를 유지한다. 계산된 `bus_endpoint_route_consistency`와 `bus_route_coverage_score`를 trace에 제공한다. 전체 700개를 실행했지만 Production 지표 변화가 없어 탈락했다.

## Candidate B — tighter stop radius

정류장 반경을 150m에서 100m로 줄여 지나가는 car/walk의 proximity evidence를 줄인다. bus/car 100개 subset에서 방향을 확인했으며, 전체 700개 Release 검증 대상 후보로 승격하지 않았다.

## Candidate C — structured bus confirmation

Final bus를 선택할 때 endpoint route consistency와 route score를 동시에 요구한다. bus/car 100개 subset에서 Bus F1이 0.1171에서 0.0637로 낮아져 탈락했다.

