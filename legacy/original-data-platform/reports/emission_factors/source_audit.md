# Emission Factors source audit

대상 파일은 `ghg-conversion-factors-2026-flat-format-revised.xlsx`이며, `Front page`와 `Factors by Category` 두 sheet를 확인했다. Factor sheet의 실제 header는 6번째 행이고, data row는 8,740개, column은 10개다.

실제 column은 `ID`, `Scope`, `Level 1`, `Level 2`, `Level 3`, `Level 4`, `Column Text`, `UOM`, `GHG/Unit`, `GHG Conversion Factor 2026`이다. 사용 가능한 UOM은 km, miles, passenger.km 등을 포함하며 GHG 단위에는 `kg CO2e`와 CO2/CH4/N2O 구성값이 함께 존재한다.

확인한 교통 category는 Passenger vehicles 864 rows, Bus 16 rows, Rail 20 rows이며, 자동차 size category는 `Cars (by size)`와 `Cars (by market segment)`로 분리되어 있다. Bus subtype은 `Local bus (not London)`, `Local London bus`, `Average local bus`, `Coach`, rail subtype은 `National rail`, `International rail`, `Light rail and tram`, `London Underground`가 실제로 존재한다.

WTT row는 771개, Battery Electric Vehicle row는 826개, Average/Unknown 표기 row는 484개다. factor가 비어 있는 row도 1,705개 존재하므로 빈 값을 임의의 0으로 바꾸지 않는다.

전체 audit 결과는 `reports/emission_factors/source_audit.json`에 저장하며 `scripts/audit_emission_source.py`로 재실행할 수 있다.
