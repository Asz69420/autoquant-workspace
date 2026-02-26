param(
  [string]$TaskName = 'OpenClaw-Daily-Intel'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $root 'scripts\pipeline\write_daily_intel_txt.py'
if (-not (Test-Path -LiteralPath $script)) { throw "Missing script: $script" }

$taskCmd = "python `"$script`" --send-telegram"
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
$ErrorActionPreference = $oldEap
& schtasks /Create /F /SC DAILY /TN $TaskName /TR $taskCmd /ST 05:30 | Out-Null

Write-Output ("Scheduled task created: " + $TaskName)
Write-Output ("Command: " + $taskCmd)
Write-Output "Time: 05:30 (set host TZ to Australia/Brisbane for AEST)"
