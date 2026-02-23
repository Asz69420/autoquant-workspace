param([int]$FreshMinutes = 5)
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $workspace

$needRestart = $false
$py = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Python314*' }
if (-not $py) { $needRestart = $true }

$outbox = Join-Path $workspace 'data\logs\outbox'
if (Test-Path $outbox) {
  $stale = Get-ChildItem $outbox -File -ErrorAction SilentlyContinue | Where-Object { ((Get-Date) - $_.LastWriteTime).TotalMinutes -gt $FreshMinutes }
  if ($stale.Count -gt 0) { $needRestart = $true }
}

if ($needRestart) {
  Start-ScheduledTask -TaskName 'AutoQuant-tg_reporter' | Out-Null
  python scripts/log_event.py --run-id oq--watchdog-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action logger_watchdog --status-word WARN --status-emoji âš ï¸ --reason-code DEPENDENCY_DOWN --summary "tg_reporter restarted by watchdog" --input tg_reporter --output restart
}
