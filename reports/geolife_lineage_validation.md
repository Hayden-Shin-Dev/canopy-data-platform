# GeoLife Lineage Validation

검증 대상은 `Geolife Trajectories 1.3.zip`에서 생성한 최종 120s purity 0.9 Window Dataset이다.

- Raw trajectory points: 24,876,977
- Raw users / trajectories: 182 / 18,670
- Canonical label intervals: bike 2,089, bus 2,853, car 2,172, rail 1,112, walk 6,460
- Processed windows: 113,718
- Processed users / trajectories: 62 / 4,440
- Raw trajectory와 일치한 processed trajectory: 4,440
- Raw에 없는 processed trajectory: 0

모든 processed user가 Raw user의 부분집합이고, canonical mode 외 label은 없으며, 다섯 mode 모두 Raw label과 processed Window에 존재한다. 품질 정책으로 분리된 `#qN` suffix는 base trajectory ID로 정규화해 비교했다. 전체 결과는 `reports/geolife_lineage_validation.json`에 저장되어 있다.
