param(
    [Parameter(Mandatory = $true)] [string[]]$VehicleArchives,
    [int]$MaxVehicleFiles = 10000,
    [string]$LinkedWindows = "data/interim/aihub/linked_vehicle_car_windows_10000.csv",
    [string]$Dataset = "data/interim/aihub/aihub_120_agg_linked_car_10000_train3.csv",
    [string]$Manifest = "data/interim/aihub/aihub_linked_car_10000_train3_manifest.json",
    [string]$Model = "data/interim/aihub/hist_120_linked_car_10000.joblib",
    [string]$Metrics = "data/interim/aihub/hist_120_linked_car_10000_metrics.json"
)

$ErrorActionPreference = "Stop"
python -m scripts.build_linked_vehicle_windows $VehicleArchives $LinkedWindows --max-files $MaxVehicleFiles --window-seconds 120
python -m scripts.prepare_linked_car_experiment data/interim/aihub/aihub_120_agg_rebuilt.csv $LinkedWindows $Dataset $Manifest --max-windows-per-user 3
python -m scripts.train_aihub_model $Dataset $Model $Metrics --model-type hist_gradient_boosting --class-weight none --feature-set all --split-manifest $Manifest --window-seconds 120
python -m scripts.validate_aihub_release $Dataset $Manifest $Model --window-seconds 120
