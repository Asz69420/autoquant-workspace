$ErrorActionPreference = 'Stop'

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$taskName = "AutoQuant-Oragorn-ContextSync"
$script = Join-Path $ROOT "scripts\automation\run-oragorn-context-sync.ps1"

if (-not (Test-Path $script)) {
  throw "Missing runner script: $script"
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '"') -WorkingDirectory $ROOT
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Refresh Oragorn CONTEXT.md + SESSION_CONTEXT.md daily" -Force | Out-Null

Write-Host "Scheduled task configured: $taskName @ 03:00 daily"
(Get-ScheduledTask -TaskName $taskName).Actions | Select-Object Execute, Arguments, WorkingDirectory | Format-List
