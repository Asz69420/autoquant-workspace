[CmdletBinding()]
param(
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'

$ROOT = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PowerShellExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$PythonExe = 'python'
$CurrentUser = "$env:USERDOMAIN\$env:USERNAME"

$GlobalSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$GlobalPrincipal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Highest

function Register-AutoQuantTask {
    param(
        [Parameter(Mandatory = $true)][string]$TaskName,
        [Parameter(Mandatory = $true)][Microsoft.Management.Infrastructure.CimInstance]$Action,
        [Parameter(Mandatory = $true)][Microsoft.Management.Infrastructure.CimInstance[]]$Triggers,
        [Parameter(Mandatory = $true)][string]$Description,
        [switch]$StartNow
    )

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Triggers `
        -Principal $GlobalPrincipal `
        -Settings $GlobalSettings `
        -Description $Description `
        -Force | Out-Null

    if ($StartNow) {
        Start-ScheduledTask -TaskName $TaskName | Out-Null
    }

    Write-Host ("OK: " + $TaskName) -ForegroundColor Green
}

function New-LoopTrigger {
    param(
        [Parameter(Mandatory = $true)][TimeSpan]$Interval,
        [int]$StartDelayMinutes = 1
    )

    # Use explicit repetition parameters for broad compatibility (WinPS 5.1 / SchTasks CIM differences)
    $startAt = (Get-Date).AddMinutes($StartDelayMinutes)
    $duration = New-TimeSpan -Days 3650
    $trigger = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval $Interval -RepetitionDuration $duration
    return $trigger
}

function New-DailyTriggers {
    param(
        [Parameter(Mandatory = $true)][string[]]$Times
    )

    $list = @()
    foreach ($t in $Times) {
        $list += New-ScheduledTaskTrigger -Daily -At $t
    }
    return $list
}

# quarter-hour helper removed; using stable loop trigger scheduling

function Assert-PathExists {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ("Missing required path: " + $Path)
    }
}

Write-Host "Registering AutoQuant scheduled tasks..." -ForegroundColor Cyan
Write-Host ("Running as: " + $CurrentUser) -ForegroundColor DarkGray
Write-Host ("Workspace: " + $ROOT) -ForegroundColor DarkGray

# Validate required scripts
$requiredPaths = @(
    (Join-Path $ROOT 'scripts\automation\run_autopilot_task.ps1'),
    (Join-Path $ROOT 'scripts\pipeline\run_youtube_watch_worker.ps1'),
    (Join-Path $ROOT 'scripts\automation\bundle-run-log.ps1'),
    (Join-Path $ROOT 'scripts\automation\run_daily_intel.ps1'),
    (Join-Path $ROOT 'scripts\pipeline\transcript_ingest_worker.py'),
    (Join-Path $ROOT 'scripts\automation\run-oragorn-context-sync.ps1'),
    (Join-Path $ROOT 'scripts\claude-tasks\run-strategy-researcher.ps1'),
    (Join-Path $ROOT 'scripts\claude-tasks\run-strategy-generator.ps1'),
    (Join-Path $ROOT 'scripts\claude-tasks\run-doctrine-synthesizer.ps1'),
    (Join-Path $ROOT 'scripts\claude-tasks\run-backtest-auditor.ps1'),
    (Join-Path $ROOT 'scripts\automation\build_queue_worker.ps1'),
    (Join-Path $ROOT 'scripts\tg_reporter.py'),
    (Join-Path $ROOT 'scripts\ops\tg_reporter_watchdog.ps1'),
    (Join-Path $ROOT 'scripts\automation\oragorn_subagent_monitor.ps1')
)
foreach ($p in $requiredPaths) { Assert-PathExists -Path $p }

$startTasks = (-not $NoStart)

# 1) AutoQuant-autopilot-user (every 15 minutes)
$autopilotScript = Join-Path $ROOT 'scripts\automation\run_autopilot_task.ps1'
$autopilotAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $autopilotScript + '"') -WorkingDirectory $ROOT
$autopilotTrigger = New-LoopTrigger -Interval (New-TimeSpan -Minutes 15)
Register-AutoQuantTask -TaskName 'AutoQuant-autopilot-user' -Action $autopilotAction -Triggers @($autopilotTrigger) -Description 'Run autopilot loop every 15 minutes' -StartNow:$startTasks

# 2) AutoQuant-youtube-watch-user (every 6 hours)
$ytScript = Join-Path $ROOT 'scripts\pipeline\run_youtube_watch_worker.ps1'
$ytAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $ytScript + '"') -WorkingDirectory $ROOT
$ytTrigger = New-LoopTrigger -Interval (New-TimeSpan -Hours 6)
Register-AutoQuantTask -TaskName 'AutoQuant-youtube-watch-user' -Action $ytAction -Triggers @($ytTrigger) -Description 'Run YouTube watch worker every 6 hours' -StartNow:$startTasks

# 3) AutoQuant-bundle-run-log-user (frodex, every 15 minutes)
$bundleScript = Join-Path $ROOT 'scripts\automation\bundle-run-log.ps1'
$bundleFrodexAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $bundleScript + '" -Pipeline frodex -WindowMinutes 16') -WorkingDirectory $ROOT
$bundleFrodexTrigger = New-LoopTrigger -Interval (New-TimeSpan -Minutes 15)
Register-AutoQuantTask -TaskName 'AutoQuant-bundle-run-log-user' -Action $bundleFrodexAction -Triggers @($bundleFrodexTrigger) -Description 'Bundle and report frodex logs every 15 minutes' -StartNow:$startTasks

# 4) AutoQuant-bundle-run-log-quandalf-user (every 2 hours)
$bundleQuandalfAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $bundleScript + '" -Pipeline quandalf -WindowMinutes 130') -WorkingDirectory $ROOT
$bundleQuandalfTrigger = New-LoopTrigger -Interval (New-TimeSpan -Hours 2)
Register-AutoQuantTask -TaskName 'AutoQuant-bundle-run-log-quandalf-user' -Action $bundleQuandalfAction -Triggers @($bundleQuandalfTrigger) -Description 'Bundle and report quandalf logs every 2 hours' -StartNow:$startTasks

# 5) AutoQuant-daily-intel-user (daily 05:30)
$dailyIntelScript = Join-Path $ROOT 'scripts\automation\run_daily_intel.ps1'
$dailyIntelAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $dailyIntelScript + '"') -WorkingDirectory $ROOT
$dailyIntelTrigger = New-DailyTriggers -Times @('05:30')
Register-AutoQuantTask -TaskName 'AutoQuant-daily-intel-user' -Action $dailyIntelAction -Triggers $dailyIntelTrigger -Description 'Generate and send daily intel summary at 05:30' -StartNow:$startTasks

# 6) AutoQuant-transcript-ingest-user (daily 09:30)
$transcriptScript = Join-Path $ROOT 'scripts\pipeline\transcript_ingest_worker.py'
$transcriptAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "' + $PythonExe + ' ''' + $transcriptScript + '''"') -WorkingDirectory $ROOT
$transcriptTrigger = New-DailyTriggers -Times @('09:30')
Register-AutoQuantTask -TaskName 'AutoQuant-transcript-ingest-user' -Action $transcriptAction -Triggers $transcriptTrigger -Description 'Ingest transcript sources daily at 09:30' -StartNow:$startTasks

# 7) AutoQuant-Oragorn-ContextSync (daily 03:00)
$contextSyncScript = Join-Path $ROOT 'scripts\automation\run-oragorn-context-sync.ps1'
$contextSyncAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $contextSyncScript + '"') -WorkingDirectory $ROOT
$contextSyncTrigger = New-DailyTriggers -Times @('03:00')
Register-AutoQuantTask -TaskName 'AutoQuant-Oragorn-ContextSync' -Action $contextSyncAction -Triggers $contextSyncTrigger -Description 'Refresh Oragorn context daily at 03:00' -StartNow:$startTasks

# 8) AutoQuant-Claude-Researcher (daily 02/06/10/14/18/22)
$claudeResearchScript = Join-Path $ROOT 'scripts\claude-tasks\run-strategy-researcher.ps1'
$claudeResearchAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $claudeResearchScript + '"') -WorkingDirectory $ROOT
$claudeResearchTriggers = New-DailyTriggers -Times @('02:00','06:00','10:00','14:00','18:00','22:00')
Register-AutoQuantTask -TaskName 'AutoQuant-Claude-Researcher' -Action $claudeResearchAction -Triggers $claudeResearchTriggers -Description 'Claude strategy researcher (6x daily)' -StartNow:$startTasks

# 9) AutoQuant-Claude-Generator (hourly odd hours)
$claudeGenScript = Join-Path $ROOT 'scripts\claude-tasks\run-strategy-generator.ps1'
$claudeGenAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $claudeGenScript + '"') -WorkingDirectory $ROOT
$claudeGenTimes = @('01:00','03:00','05:00','07:00','09:00','11:00','13:00','15:00','17:00','19:00','21:00','23:00')
$claudeGenTriggers = New-DailyTriggers -Times $claudeGenTimes
Register-AutoQuantTask -TaskName 'AutoQuant-Claude-Generator' -Action $claudeGenAction -Triggers $claudeGenTriggers -Description 'Claude strategy generator (12x daily)' -StartNow:$startTasks

# 10) AutoQuant-Claude-Doctrine (daily 04:00)
$claudeDoctrineScript = Join-Path $ROOT 'scripts\claude-tasks\run-doctrine-synthesizer.ps1'
$claudeDoctrineAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $claudeDoctrineScript + '"') -WorkingDirectory $ROOT
$claudeDoctrineTrigger = New-DailyTriggers -Times @('04:00')
Register-AutoQuantTask -TaskName 'AutoQuant-Claude-Doctrine' -Action $claudeDoctrineAction -Triggers $claudeDoctrineTrigger -Description 'Claude doctrine synthesizer daily at 04:00' -StartNow:$startTasks

# 11) AutoQuant-Claude-Auditor (daily 05:00)
$claudeAuditScript = Join-Path $ROOT 'scripts\claude-tasks\run-backtest-auditor.ps1'
$claudeAuditAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $claudeAuditScript + '"') -WorkingDirectory $ROOT
$claudeAuditTrigger = New-DailyTriggers -Times @('05:00')
Register-AutoQuantTask -TaskName 'AutoQuant-Claude-Auditor' -Action $claudeAuditAction -Triggers $claudeAuditTrigger -Description 'Claude backtest auditor daily at 05:00' -StartNow:$startTasks

# 12) AutoQuant-build-queue-worker (every 1 minute; Task Scheduler does not support <1m repetition)
$buildQueueScript = Join-Path $ROOT 'scripts\automation\build_queue_worker.ps1'
$buildQueueAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $buildQueueScript + '"') -WorkingDirectory $ROOT
$buildQueueTrigger = New-LoopTrigger -Interval (New-TimeSpan -Minutes 1)
Register-AutoQuantTask -TaskName 'AutoQuant-build-queue-worker' -Action $buildQueueAction -Triggers @($buildQueueTrigger) -Description 'Build queue worker every 1 minute' -StartNow:$startTasks

# 13) AutoQuant-tg_reporter (startup + every 2 minutes)
$tgReporterScript = Join-Path $ROOT 'scripts\tg_reporter.py'
$tgReporterAction = New-ScheduledTaskAction -Execute $PythonExe -Argument ('"' + $tgReporterScript + '" --daemon --interval 15') -WorkingDirectory $ROOT
$tgStartTrigger = New-ScheduledTaskTrigger -AtStartup
$tgRepeatTrigger = New-LoopTrigger -Interval (New-TimeSpan -Minutes 2) -StartDelayMinutes 0
Register-AutoQuantTask -TaskName 'AutoQuant-tg_reporter' -Action $tgReporterAction -Triggers @($tgStartTrigger, $tgRepeatTrigger) -Description 'Telegram reporter daemon with startup + repeat triggers' -StartNow:$startTasks

# 14) AutoQuant-tg_reporter-watchdog (every 2 minutes)
$tgWatchdogScript = Join-Path $ROOT 'scripts\ops\tg_reporter_watchdog.ps1'
$tgWatchdogAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $tgWatchdogScript + '"') -WorkingDirectory $ROOT
$tgWatchdogTrigger = New-LoopTrigger -Interval (New-TimeSpan -Minutes 2) -StartDelayMinutes 0
Register-AutoQuantTask -TaskName 'AutoQuant-tg_reporter-watchdog' -Action $tgWatchdogAction -Triggers @($tgWatchdogTrigger) -Description 'Watchdog for tg_reporter every 2 minutes' -StartNow:$startTasks

# 15) AutoQuant-Oragorn-Subagent-Monitor (at logon; daemon loop inside script)
$oragornMonitorScript = Join-Path $ROOT 'scripts\automation\oragorn_subagent_monitor.ps1'
$oragornMonitorAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $oragornMonitorScript + '"') -WorkingDirectory $ROOT
$oragornMonitorTrigger = New-ScheduledTaskTrigger -AtLogOn
Register-AutoQuantTask -TaskName 'AutoQuant-Oragorn-Subagent-Monitor' -Action $oragornMonitorAction -Triggers @($oragornMonitorTrigger) -Description 'Monitor Oragorn sub-agent sessions continuously from logon' -StartNow:$startTasks

Write-Host ''
Write-Host 'All AutoQuant scheduled tasks registered.' -ForegroundColor Cyan
Write-Host 'Tasks included:' -ForegroundColor Cyan
@(
    'AutoQuant-autopilot-user',
    'AutoQuant-youtube-watch-user',
    'AutoQuant-bundle-run-log-user',
    'AutoQuant-bundle-run-log-quandalf-user',
    'AutoQuant-daily-intel-user',
    'AutoQuant-transcript-ingest-user',
    'AutoQuant-Oragorn-ContextSync',
    'AutoQuant-Claude-Researcher',
    'AutoQuant-Claude-Generator',
    'AutoQuant-Claude-Doctrine',
    'AutoQuant-Claude-Auditor',
    'AutoQuant-build-queue-worker',
    'AutoQuant-tg_reporter',
    'AutoQuant-tg_reporter-watchdog',
    'AutoQuant-Oragorn-Subagent-Monitor'
) | ForEach-Object { Write-Host (' - ' + $_) }

Write-Host ''
Write-Host 'Verification command:' -ForegroundColor DarkGray
Write-Host "Get-ScheduledTask | Where-Object { `$_.TaskName -like 'AutoQuant-*' } | Sort-Object TaskName | Format-Table TaskName,State"
