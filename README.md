# Canopy Emission Factors

## 목적

Canopy의 canonical mode별 operational travel emission factor를 공식 source에서 추출하고, subtype·차량 fuel/size 정보가 있을 때 가장 구체적인 factor를 선택한다.

## Source

UK Government `Greenhouse gas reporting: conversion factors 2026` flat-format workbook. 실제 구조는 `Factors by Category` sheet의 6번째 header와 10개 column을 기준으로 parser가 읽는다. 원본에 없는 값은 만들지 않는다.

## Canonical mode

`walk`, `bike`, `car`, `bus`, `rail`

walk와 conventional bicycle은 Canopy v1 operational boundary에서 0 gCO2e/person.km 정책값을 사용한다. e-bike는 포함하지 않는다.

## Mapping과 fallback

- car: petrol, diesel, hybrid, plug-in hybrid, battery electric, CNG, LPG, unknown × small/medium/large/average
- bus: local bus, London bus, average local bus, coach
- rail: national rail, international rail, light rail and tram, underground
- fallback: exact → average/unknown 공식 row → unresolved error

car factor는 `gCO2e/vehicle.km`, bus·rail은 `gCO2e/passenger.km`로 정규화하며 원본 `kg CO2e` 값과 source row ID를 함께 보존한다. POC 차량 occupancy assumption은 1이다.

## 산출물

- `data/processed/emission_factors/emission_factors_2026.csv`
- `reports/emission_factors/source_audit.json`
- `reports/emission_factors/validation.json`
- `reports/emission_factors/sample_factor_resolution.json`

## 실행

```powershell
./scripts/rebuild_emission_factors.ps1 -SourceWorkbook "C:/path/ghg-conversion-factors-2026-flat-format-revised.xlsx"
py -3.13 -m pytest -q
```

Transit Context에서 subtype을 제공하면 `FactorResolver.resolve_emission_factor`에 전달한다. 이 branch에서는 버스·철도 API나 실제 한국 배출계수를 추가하지 않는다.
