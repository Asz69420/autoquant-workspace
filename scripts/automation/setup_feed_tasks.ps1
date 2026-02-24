param(
  [int]$YouTubeHours = 2,
  [int]$TVHours = 12,
  [int]$AutopilotHours = 6
)

$ErrorActionPreference = 'Stop'
$wd = (Get-Location).Path

function Register-LoopTask($taskName, $scriptArgs, $hours) {
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ("-ExecutionPolicy Bypass -Command \"cd '$wd'; $scriptArgs\"")
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
  $trigger.RepetitionInterval = (New-TimeSpan -Hours $hours)
  $trigger.RepetitionDuration = ([TimeSpan]::MaxValue)
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
}

Register-LoopTask '\AutoQuant-youtube-watch' 'python scripts/pipeline/youtube_watch_worker.py' $YouTubeHours
Register-LoopTask '\AutoQuant-tv-catalog' 'python scripts/pipeline/tv_catalog_worker.py' $TVHours
Register-LoopTask '\AutoQuant-autopilot' 'powershell -ExecutionPolicy Bypass -File scripts/pipeline/autopilot_worker.ps1 -RunYouTubeWatcher -RunTVCatalogWorker -MaxBundlesPerRun 1 -MaxRefinementsPerRun 1' $AutopilotHours

Write-Output ('Tasks ensured: AutoQuant-youtube-watch/' + $YouTubeHours + 'h, AutoQuant-tv-catalog/' + $TVHours + 'h, AutoQuant-autopilot/' + $AutopilotHours + 'h')