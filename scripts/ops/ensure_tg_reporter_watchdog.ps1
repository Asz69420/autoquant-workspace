param(
  [int]$Minutes = 2
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = 'C:\Users\Clamps\AppData\Local\Programs\Python\Python314\python.exe'
$reporterScript = Join-Path $workspace 'scripts\tg_reporter.py'
$watchScript = Join-Path $workspace 'scripts\ops\tg_reporter_watchdog.ps1'

if (-not (Test-Path $watchScript)) {
@'
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
  python scripts/log_event.py --run-id oq--watchdog-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action logger_watchdog --status-word WARN --status-emoji ⚠️ --reason-code DEPENDENCY_DOWN --summary "tg_reporter restarted by watchdog" --input tg_reporter --output restart
}
'@ | Set-Content -Path $watchScript -Encoding UTF8
}

# Ensure primary task has startup + repeating trigger and restart policy.
$action = New-ScheduledTaskAction -Execute $python -Argument "$reporterScript --daemon --interval 15" -WorkingDirectory $workspace
$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date
$repeatTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $Minutes) -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'AutoQuant-tg_reporter' -Action $action -Trigger @($startupTrigger,$repeatTrigger) -Principal $principal -Settings $settings -Force | Out-Null

# Create watchdog task
$watchAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File \"$watchScript\""
$watchTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date
$watchTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes $Minutes) -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition
$watchSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'AutoQuant-tg_reporter-watchdog' -Action $watchAction -Trigger $watchTrigger -Principal $principal -Settings $watchSettings -Force | Out-Null

Start-ScheduledTask -TaskName 'AutoQuant-tg_reporter' | Out-Null
Start-ScheduledTask -TaskName 'AutoQuant-tg_reporter-watchdog' | Out-Null
Write-Output 'OK: tg_reporter + watchdog ensured'
