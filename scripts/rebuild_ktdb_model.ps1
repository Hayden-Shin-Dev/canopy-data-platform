param(
    [string]$Dataset = "data/processed/population_baseline/ktdb/01_population_model_training_all.csv",
    [string]$Model = "models/expected_behaviour/ktdb_population_baseline.pkl",
    [string]$Report = "reports/integration/runs/ktdb_candidate_comparison.json"
)

$ErrorActionPreference = "Stop"

python -m scripts.experiment_ktdb_candidates `
    $Dataset `
    $Model `
    $Report `
    --selected-model $Model
