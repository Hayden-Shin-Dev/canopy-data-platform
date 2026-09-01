param(
    [string]$SplitWindows = "data/interim/aihub/aihub_split_windows.csv",
    [string]$SplitManifest = "data/interim/aihub/aihub_split_manifest.json",
    [string]$AggregateWindows = "data/interim/aihub/aihub_120_agg_rebuilt.csv",
    [string]$Model = "models/mobility_recognition/aihub_hist120.joblib",
    [string]$Metrics = "data/interim/aihub/aihub_hist120_metrics.json"
)

$ErrorActionPreference = "Stop"

# Keep the rebuild deterministic: aggregate adjacent same-mode 60s rows, then train
# the validation-selected HistGradientBoosting contract used by production.
python -m scripts.aggregate_aihub_windows $SplitWindows $AggregateWindows
python -m scripts.train_aihub_model $AggregateWindows $Model $Metrics `
    --model-type hist_gradient_boosting `
    --class-weight none `
    --feature-set all `
    --split-manifest $SplitManifest `
    --window-seconds 120
python -m scripts.validate_aihub_release $AggregateWindows $SplitManifest $Model --window-seconds 120
