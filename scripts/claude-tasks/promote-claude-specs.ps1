# Promote Quandalf's strategy specs into the pipeline for backtesting
# Copies from artifacts/claude-specs/ to artifacts/strategy_specs/YYYYMMDD/
# and registers each in INDEX.json via the existing update_index pattern

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$today = Get-Date -Format "yyyyMMdd"
$targetDir = "$ROOT\artifacts\strategy_specs\$today"
$sourceDir = "$ROOT\artifacts\claude-specs"
$indexPath = "$ROOT\artifacts\strategy_specs\INDEX.json"

if (-not (Test-Path $sourceDir)) {
    Write-Host "No claude-specs directory"
    exit 0
}

$specs = Get-ChildItem $sourceDir -Filter "*.strategy_spec.json" -ErrorAction SilentlyContinue
if ($specs.Count -eq 0) {
    Write-Host "No specs to promote"
    exit 0
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

# Load existing index
$index = @()
if (Test-Path $indexPath) {
    try {
        $index = @(Get-Content $indexPath -Raw | ConvertFrom-Json)
    }
    catch {
        $index = @()
    }
}

$promoted = 0
foreach ($spec in $specs) {
    $dest = Join-Path $targetDir $spec.Name
    if (Test-Path $dest) {
        Write-Host "SKIP (already exists): $($spec.Name)"
        continue
    }

    Copy-Item $spec.FullName $dest

    $pointer = "artifacts/strategy_specs/$today/$($spec.Name)"
    $index = @($pointer) + @($index | Where-Object { $_ -ne $pointer })

    $promoted++
    Write-Host "PROMOTED: $($spec.Name)"
}

# Write updated index (cap at 200)
$index = $index | Select-Object -First 200
$index | ConvertTo-Json | Set-Content $indexPath -Encoding UTF8

# Remove promoted specs from staging
foreach ($spec in $specs) {
    $dest = Join-Path $targetDir $spec.Name
    if (Test-Path $dest) {
        Remove-Item $spec.FullName -Force
        Write-Host "CLEANED: $($spec.Name) from claude-specs/"
    }
}

Write-Host "Done: promoted $promoted specs to pipeline"
