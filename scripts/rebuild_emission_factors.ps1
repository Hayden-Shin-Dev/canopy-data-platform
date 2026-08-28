param(
    [Parameter(Mandatory = $true)]
    [string]$SourceWorkbook,
    [string]$OutputDir = "data/processed/emission_factors",
    [string]$ReportDir = "reports/emission_factors"
)

$ErrorActionPreference = "Stop"
py -3.13 -m src.emission_factors.parser $SourceWorkbook "$OutputDir/emission_factors_2026.csv" > $null
py -3.13 -m scripts.validate_emission_factors "$OutputDir/emission_factors_2026.csv" --source-workbook $SourceWorkbook --output "$ReportDir/validation.json"
py -3.13 -m scripts.generate_emission_sample $SourceWorkbook --output "$ReportDir/sample_factor_resolution.json"
