param(
  [int]$YouTubeHours = 24,
  [int]$TVHours = 12,
  [int]$AutopilotMinutes = 15,
  [switch]$YouTubeDaily = $true,
  [string]$YouTubeDailyAt = '08:10'
)

$ErrorActionPreference = 'Stop'
$wd = (Get-Location).Path

function Register-LoopTask($taskName, $scriptArgs, [TimeSpan]$interval) {
  $arg = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "cd ''' + $wd + '''; ' + $scriptArgs + '"'
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
  $trigger.RepetitionInterval = $interval
  $trigger.RepetitionDuration = ([TimeSpan]::MaxValue)
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
}

function Register-DailyTask($taskName, $scriptArgs, [string]$timeAt) {
  $arg = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "cd ''' + $wd + '''; ' + $scriptArgs + '"'
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
  $trigger = New-ScheduledTaskTrigger -Daily -At $timeAt
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
}

if ($YouTubeDaily) {
  Register-DailyTask '\AutoQuant-youtube-watch' 'python scripts/pipeline/youtube_watch_worker.py' $YouTubeDailyAt
} else {
  Register-LoopTask '\AutoQuant-youtube-watch' 'python scripts/pipeline/youtube_watch_worker.py' (New-TimeSpan -Hours $YouTubeHours)
}
Register-LoopTask '\AutoQuant-tv-catalog' 'python scripts/pipeline/tv_catalog_worker.py' (New-TimeSpan -Hours $TVHours)
Register-LoopTask '\AutoQuant-autopilot' 'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File scripts/pipeline/autopilot_worker.ps1 -RunYouTubeWatcher -RunTVCatalogWorker -MaxBundlesPerRun 3 -MaxRefinementsPerRun 1' (New-TimeSpan -Minutes $AutopilotMinutes)

$ytMode = if ($YouTubeDaily) { ('daily@' + $YouTubeDailyAt) } else { ($YouTubeHours.ToString() + 'h') }
Write-Output ('Tasks ensured: AutoQuant-youtube-watch/' + $ytMode + ', AutoQuant-tv-catalog/' + $TVHours + 'h, AutoQuant-autopilot/' + $AutopilotMinutes + 'm')