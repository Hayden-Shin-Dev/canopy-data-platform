# Integration local test guide

저장소 루트에서 실행합니다.

## Replay CLI

```powershell
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --speed instant
python scripts/replay_integration.py data/fixtures/integration/quality_edge_cases.csv --speed instant
python scripts/replay_integration.py data/fixtures/integration/seoul_bus_route.csv --pipeline
```

`--pipeline`은 repository의 GeoLife model artifact, KTDB model, emission factor table이 모두 있어야 PASS가 됩니다. 누락된 artifact를 임의로 만들지 않습니다.

## Local UI

```powershell
python scripts/run_integration_ui.py
```

브라우저에서 `http://127.0.0.1:8765`를 열고 fixture와 replay speed(1x/5x/10x/30x/Instant)를 선택합니다. Start/Pause/Resume/Stop으로 lifecycle을 확인하고, GPS Replay 표에서 각 event의 accepted/rejected 이유를 확인합니다. KTDB Expected Behaviour 입력란에는 `src/ktdb/schema.py`의 `MODEL_FEATURES` 19개를 JSON으로 넣어야 최종 pipeline을 시도합니다.

## Automated checks

```powershell
pytest -q tests/test_gps_contract.py tests/test_integration_distance.py tests/test_integration_ingestion.py tests/test_integration_replay.py tests/test_integration_geolife_adapter.py tests/test_integration_expected_behaviour.py tests/test_integration_emissions.py tests/test_integration_pipeline.py tests/test_integration_ui.py
```

실제 production replay는 Desktop의 `models/mobility_recognition/geolife_hardened_120s_purity_090.joblib`, KTDB model, processed dataset, 서울 Transit reference를 사용합니다. artifact가 누락되면 성공으로 대체하지 않고 validation에서 실패 원인을 표시합니다.
