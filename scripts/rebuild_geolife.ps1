param(
    [Parameter(Mandatory = $true)]
    [string]$RawZip,
    [string]$OutputRoot = "data/processed/mobility_recognition",
    [string]$ModelRoot = "models/mobility_recognition"
)

$ErrorActionPreference = "Stop"

py -3.13 -m scripts.build_geolife_windows `
    $RawZip `
    "$OutputRoot/geolife_windows_30s.csv" `
    --window-seconds 30 `
    --min-points 2 `
    --min-label-coverage 0.5

py -3.13 -m scripts.assign_geolife_splits `
    "$OutputRoot/geolife_windows_30s.csv" `
    "$OutputRoot/geolife_windows_30s_split.csv" `
    --seed 2021

# 60초 split을 기준으로 Window 길이 비교와 최종 120초 모델을 재현한다.
py -3.13 -m scripts.build_geolife_windows `
    $RawZip `
    "$OutputRoot/geolife_windows_60s.csv" `
    --window-seconds 60 `
    --min-points 2 `
    --min-label-coverage 0.5

py -3.13 -m scripts.assign_geolife_splits `
    "$OutputRoot/geolife_windows_60s.csv" `
    "$OutputRoot/geolife_windows_60s_split.csv" `
    --seed 2021

py -3.13 -m scripts.build_geolife_windows `
    $RawZip `
    "$OutputRoot/geolife_windows_120s.csv" `
    --window-seconds 120 `
    --min-points 2 `
    --min-label-coverage 0.5 `
    --min-mode-purity 0.9

py -3.13 -m scripts.assign_geolife_splits `
    "$OutputRoot/geolife_windows_120s.csv" `
    "$OutputRoot/geolife_windows_120s_split.csv" `
    --reference-split-csv "$OutputRoot/geolife_windows_60s_split.csv"

py -3.13 -m scripts.train_geolife_baseline `
    "$OutputRoot/geolife_windows_120s_split.csv" `
    "$ModelRoot/geolife_120s_purity_090.joblib" `
    "$OutputRoot/geolife_120s_purity_090_metrics.json" `
    --class-weight none `
    --model-type random_forest `
    --n-estimators 100 `
    --random-seed 2021

py -3.13 -m scripts.evaluate_geolife_model `
    "$OutputRoot/geolife_windows_120s_split.csv" `
    "$ModelRoot/geolife_120s_purity_090.joblib" `
    --split test `
    --output "$OutputRoot/geolife_final_test_metrics.json"
