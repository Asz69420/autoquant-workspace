param(
  [switch]$Apply
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$python = "python"

$runnerCmd = "cd /d $ROOT && $python scripts/forward/forward_runner.py"
$healthCmd = "cd /d $ROOT && $python scripts/forward/check_runner_health.py"
$weeklyCmd = "cd /d $ROOT && $python scripts/forward/generate_weekly_scorecard.py"

function Ensure-Task($Name, $Trigger, $Command) {
  $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $Command"
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
  $task = New-ScheduledTask -Action $action -Principal $principal -Trigger $Trigger -Settings $settings

  if ($Apply) {
    Register-ScheduledTask -TaskName $Name -InputObject $task -Force | Out-Null
    Write-Host "Updated task: $Name"
  } else {
    Write-Host "DRYRUN task: $Name"
    Write-Host "  command: $Command"
  }
}

$triggers4h = @(
  (New-ScheduledTaskTrigger -Daily -At "12:05AM")
  (New-ScheduledTaskTrigger -Daily -At "4:05AM")
  (New-ScheduledTaskTrigger -Daily -At "8:05AM")
  (New-ScheduledTaskTrigger -Daily -At "12:05PM")
  (New-ScheduledTaskTrigger -Daily -At "4:05PM")
  (New-ScheduledTaskTrigger -Daily -At "8:05PM")
)

$healthTriggers = @(
  (New-ScheduledTaskTrigger -Daily -At "12:25AM")
  (New-ScheduledTaskTrigger -Daily -At "4:25AM")
  (New-ScheduledTaskTrigger -Daily -At "8:25AM")
  (New-ScheduledTaskTrigger -Daily -At "12:25PM")
  (New-ScheduledTaskTrigger -Daily -At "4:25PM")
  (New-ScheduledTaskTrigger -Daily -At "8:25PM")
)

$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "7:00AM"

Ensure-Task -Name "AutoQuant-Forward-Runner" -Trigger $triggers4h -Command $runnerCmd
Ensure-Task -Name "AutoQuant-Forward-Health" -Trigger $healthTriggers -Command $healthCmd
Ensure-Task -Name "AutoQuant-Forward-Weekly" -Trigger $weeklyTrigger -Command $weeklyCmd
