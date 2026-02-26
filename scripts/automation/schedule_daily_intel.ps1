param(
  [string]$TaskName = 'AutoQuant-daily-intel-user'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runner = Join-Path $root 'scripts\automation\run_daily_intel.ps1'
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing runner: $runner" }

$taskCmd = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
$ErrorActionPreference = $oldEap

& schtasks /Create /F /SC DAILY /TN $TaskName /TR $taskCmd /ST 05:30 | Out-Null

Write-Output ("Scheduled task created: " + $TaskName)
Write-Output ("Command: " + $taskCmd)
Write-Output "Time: 05:30 Australia/Brisbane"
