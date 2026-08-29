param(
    [string]$RawDir = "data/raw/ktdb",
    [string]$OutputDir = "data/processed/population_baseline/ktdb",
    [int]$Chunksize = 50000,
    [switch]$CleanOutput,
    [switch]$RefreshSgis,
    [double]$SgisTimeout = 20.0,
    [int]$SgisMaxRetries = 3,
    [double]$SgisRequestInterval = 0.2
)

$ErrorActionPreference = "Stop"

if ($CleanOutput -and (Test-Path -LiteralPath $OutputDir)) {
    # 생성 산출물만 지우고 raw 경로에는 손대지 않는다.
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}

$SgisRefreshArgs = @()
if ($RefreshSgis) {
    $SgisRefreshArgs = @("--refresh-sgis")
}

py -3.13 -m src.build_population_dataset `
    --raw-dir $RawDir `
    --output-dir $OutputDir `
    --chunksize $Chunksize `
    --lookup-min-samples 100 `
    --centroid-file "data/reference/admin_dong_centroids_2021.csv" `
    --sgis-timeout $SgisTimeout `
    --sgis-max-retries $SgisMaxRetries `
    --sgis-request-interval $SgisRequestInterval `
    @SgisRefreshArgs

py -3.13 -m src.validate_dataset `
    --dataset (Join-Path $OutputDir "01_population_model_training_all.csv")
