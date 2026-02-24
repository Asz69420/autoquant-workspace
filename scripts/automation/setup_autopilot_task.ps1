param(
  [int]$Hours = 6
)

$ErrorActionPreference = 'Stop'

$taskName = '\\AutoQuant-autopilot'
$wd = (Get-Location).Path
$script = Join-Path $wd 'scripts\pipeline\autopilot_worker.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-ExecutionPolicy Bypass -File "' + $script + '"')
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.RepetitionInterval = (New-TimeSpan -Hours $Hours)
$trigger.RepetitionDuration = ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output ("Task created: " + $taskName + " every " + $Hours + " hours")
