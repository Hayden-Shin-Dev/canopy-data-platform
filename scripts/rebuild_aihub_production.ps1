param(
    [string]$SourceRoot = $env:AIHUB_DATA_ROOT,
    [string]$SplitManifest = "data/interim/aihub/aihub_split_manifest.json",
    [string]$TrueWindows = "data/interim/aihub/aihub_120s_canonical_cadence_train.csv",
    [string[]]$VehicleArchives = @(),
    [int]$MaxVehicleFiles = 10000,
    [string]$Model = "models/mobility_recognition/aihub_canonical_raw120.joblib",
    [string]$Metrics = "data/interim/aihub/aihub_canonical_raw120_metrics.json"
)

$ErrorActionPreference = "Stop"

# 120초 Feature는 60초 요약값을 합치지 않고 원본 GPS point에서 다시 계산한다.
if (-not $SourceRoot -or -not (Test-Path -LiteralPath $SourceRoot)) {
    throw "Set -SourceRoot or AIHUB_DATA_ROOT to the AI-Hub 01-1.정식개방데이터 directory."
}

python -m scripts.build_aihub_duration_windows $SourceRoot $SplitManifest $TrueWindows --train-cadences 2,5,10

if ($VehicleArchives.Count -gt 0) {
    $linked = "data/interim/aihub/linked_vehicle_car_windows_$MaxVehicleFiles.csv"
    $augmented = "data/interim/aihub/aihub_120_agg_linked_car_train3.csv"
    $augmentedManifest = "data/interim/aihub/aihub_linked_car_train3_manifest.json"
    python -m scripts.build_linked_vehicle_windows $VehicleArchives $linked --max-files $MaxVehicleFiles --window-seconds 120
    python -m scripts.prepare_linked_car_experiment $TrueWindows $linked $augmented $augmentedManifest --max-windows-per-user 3
    $TrueWindows = $augmented
    $SplitManifest = $augmentedManifest
}
python -m scripts.train_aihub_model $TrueWindows $Model $Metrics `
    --model-type hist_gradient_boosting `
    --class-weight none `
    --feature-set robust `
    --split-manifest $SplitManifest `
    --window-seconds 120
python -m scripts.validate_aihub_release $TrueWindows $SplitManifest $Model --window-seconds 120
