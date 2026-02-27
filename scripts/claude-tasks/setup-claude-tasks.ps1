$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$TASKS_DIR = "$ROOT\scripts\claude-tasks"

$pwshPath = $null
$pwshCmd = Get-Command pwsh -ErrorAction SilentlyContinue
if ($pwshCmd) { $pwshPath = $pwshCmd.Source }
if (-not $pwshPath) { $pwshPath = (Get-Command powershell).Source }

Write-Host "Setting up Claude Code scheduled tasks..." -ForegroundColor Cyan

# Strategy Researcher — every 4 hours (6x/day)
$action = New-ScheduledTaskAction -Execute $pwshPath -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TASKS_DIR\run-strategy-researcher.ps1`"" -WorkingDirectory $ROOT
$triggers = @("02:00","06:00","10:00","14:00","18:00","22:00") | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName "AutoQuant-Claude-Researcher" -Action $action -Trigger $triggers -Settings $settings -Description "Claude: Strategy research every 4h" -Force
Write-Host " OK: AutoQuant-Claude-Researcher (6x/day)" -ForegroundColor Green

# Strategy Generator — every 2 hours (12x/day)
$action = New-ScheduledTaskAction -Execute $pwshPath -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TASKS_DIR\run-strategy-generator.ps1`"" -WorkingDirectory $ROOT
$triggers = @()
for ($h = 1; $h -lt 24; $h += 2) { $triggers += New-ScheduledTaskTrigger -Daily -At ("{0:D2}:00" -f $h) }
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName "AutoQuant-Claude-Generator" -Action $action -Trigger $triggers -Settings $settings -Description "Claude: Creative specs every 2h" -Force
Write-Host " OK: AutoQuant-Claude-Generator (12x/day)" -ForegroundColor Green

# Doctrine Synthesizer — daily 4am
$action = New-ScheduledTaskAction -Execute $pwshPath -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TASKS_DIR\run-doctrine-synthesizer.ps1`"" -WorkingDirectory $ROOT
$trigger = New-ScheduledTaskTrigger -Daily -At "04:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName "AutoQuant-Claude-Doctrine" -Action $action -Trigger $trigger -Settings $settings -Description "Claude: Doctrine cleanup daily 4am" -Force
Write-Host " OK: AutoQuant-Claude-Doctrine (daily 4am)" -ForegroundColor Green

# Backtest Auditor — daily 5am
$action = New-ScheduledTaskAction -Execute $pwshPath -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$TASKS_DIR\run-backtest-auditor.ps1`"" -WorkingDirectory $ROOT
$trigger = New-ScheduledTaskTrigger -Daily -At "05:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName "AutoQuant-Claude-Auditor" -Action $action -Trigger $trigger -Settings $settings -Description "Claude: Overfit detection daily 5am" -Force
Write-Host " OK: AutoQuant-Claude-Auditor (daily 5am)" -ForegroundColor Green

# Firewall — placeholder, not scheduled yet
Write-Host " SKIP: AutoQuant-Claude-Firewall (placeholder, not scheduled)" -ForegroundColor Yellow

Write-Host "`nAll active tasks registered! (~20 runs/day)" -ForegroundColor Cyan
Write-Host "Verify: Get-ScheduledTask | Where-Object {`$_.TaskName -like 'AutoQuant-Claude*'} | Format-Table TaskName, State" -ForegroundColor Gray