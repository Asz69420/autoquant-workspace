param(
  [int]$IntervalSeconds = 30
)

$ErrorActionPreference = 'Stop'

$taskName = 'AutoQuant-build-queue-worker'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$workerScript = Join-Path $repoRoot 'scripts\automation\build_queue_worker.ps1'
$powershellExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

$action = New-ScheduledTaskAction -Execute $powershellExe -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$workerScript`"" -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.RepetitionInterval = (New-TimeSpan -Seconds $IntervalSeconds)
$trigger.RepetitionDuration = (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
Write-Output "Scheduled task configured: \$taskName (every $IntervalSeconds sec)"
