param(
    [Parameter(Mandatory=$false)]
    [string]$Prompt = "A person walks forward quickly, then stops and waves.",

    [Parameter(Mandatory=$false)]
    [string]$Model = "models\kimodo-soma-rp-v1.1-f32.gguf",

    [Parameter(Mandatory=$false)]
    [string]$TextBundle = "generated\llm2vec-text-bundle",

    [Parameter(Mandatory=$false)]
    [int]$Frames = 60,

    [Parameter(Mandatory=$false)]
    [int]$Steps = 20,

    [Parameter(Mandatory=$false)]
    [int]$Seed = 42,

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "output"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$env:PATH = "$scriptDir\build\bin\Release;$scriptDir\build\Release;$env:PATH"

if (-not (Test-Path "$scriptDir\build\Release\kmd-generate.exe")) {
    Write-Error "kmd-generate.exe not found. Please build the project first."
}

if (-not (Test-Path "$scriptDir\$Model")) {
    Write-Error "Model file not found: $Model. Run 'python scripts\download_gguf_weights.py' first."
}

New-Item -ItemType Directory -Force -Path "$scriptDir\$OutputDir" | Out-Null
$promptFile = "$scriptDir\$OutputDir\prompt.txt"
Set-Content -Path $promptFile -Value $Prompt -Encoding UTF8

Write-Host "Running Kimodo Motion Generation..." -ForegroundColor Cyan
Write-Host "  Prompt:  $Prompt"
Write-Host "  Model:   $Model"
Write-Host "  Frames:  $Frames"
Write-Host "  Steps:   $Steps"
Write-Host "  Seed:    $Seed"
Write-Host "  Output:  $OutputDir"

& "$scriptDir\build\Release\kmd-generate.exe" "$scriptDir\$Model" "$scriptDir\$TextBundle" $promptFile $Frames $Steps $Seed "$scriptDir\$OutputDir"

Write-Host "`nGeneration complete! Output saved to $OutputDir\" -ForegroundColor Green
