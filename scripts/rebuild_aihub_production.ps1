param(
    [string]$SplitWindows = "data/interim/aihub/aihub_split_windows.csv",
    [string]$SplitManifest = "data/interim/aihub/aihub_split_manifest.json",
    [string]$AggregateWindows = "data/interim/aihub/aihub_120_agg_rebuilt.csv",
    [string[]]$VehicleArchives = @(),
    [int]$MaxVehicleFiles = 10000,
    [string]$Model = "models/mobility_recognition/aihub_hist120.joblib",
    [string]$Metrics = "data/interim/aihub/aihub_hist120_metrics.json"
)

$ErrorActionPreference = "Stop"

# Keep the rebuild deterministic: aggregate adjacent same-mode 60s rows, then train
# the validation-selected HistGradientBoosting contract used by production.
if ($VehicleArchives.Count -gt 0) {
    $linked = "data/interim/aihub/linked_vehicle_car_windows_$MaxVehicleFiles.csv"
    $augmented = "data/interim/aihub/aihub_120_agg_linked_car_train3.csv"
    $augmentedManifest = "data/interim/aihub/aihub_linked_car_train3_manifest.json"
    python -m scripts.build_linked_vehicle_windows $VehicleArchives $linked --max-files $MaxVehicleFiles --window-seconds 120
    python -m scripts.prepare_linked_car_experiment $AggregateWindows $linked $augmented $augmentedManifest --max-windows-per-user 3
    $AggregateWindows = $augmented
    $SplitManifest = $augmentedManifest
}
else {
    python -m scripts.aggregate_aihub_windows $SplitWindows $AggregateWindows
}
python -m scripts.train_aihub_model $AggregateWindows $Model $Metrics `
    --model-type hist_gradient_boosting `
    --class-weight none `
    --feature-set all `
    --split-manifest $SplitManifest `
    --window-seconds 120
python -m scripts.validate_aihub_release $AggregateWindows $SplitManifest $Model --window-seconds 120
