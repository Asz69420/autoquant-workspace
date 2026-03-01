$ErrorActionPreference = 'Stop'

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$python = "python"
$script = Join-Path $ROOT "scripts\automation\update_oragorn_context.py"

if (-not (Test-Path $script)) {
  Write-Error "Missing script: $script"
}

& $python $script
if ($LASTEXITCODE -ne 0) {
  Write-Error "Oragorn context sync failed with exit code $LASTEXITCODE"
}

Write-Host "Oragorn context sync complete"
