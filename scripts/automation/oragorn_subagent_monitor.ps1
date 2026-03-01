[CmdletBinding()]
param(
    [int]$IntervalSeconds = 15,
    [int]$RecentWindowSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$sessionsDir = 'C:\Users\Clamps\.openclaw\agents\oragorn\sessions'
$sessionFilePattern = '*.jsonl.deleted.*'
$stateDir = Join-Path $workspace 'data\state'
$stateFile = Join-Path $stateDir 'oragorn_logged_sessions.txt'
$logDir = Join-Path $workspace 'data\logs'
$monitorLog = Join-Path $logDir 'oragorn_subagent_monitor.log'
$wrapperScript = Join-Path $workspace 'scripts\automation\oragorn_action_wrapper.ps1'
$bundleScript = Join-Path $workspace 'scripts\automation\bundle-run-log.ps1'

function Write-MonitorLog {
    param(
        [string]$Level,
        [string]$Message
    )

    $line = ('{0} [{1}] {2}' -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'), $Level.ToUpperInvariant(), $Message)
    Write-Host $line
    Add-Content -Path $monitorLog -Value $line -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
if (-not (Test-Path -LiteralPath $stateFile)) {
    New-Item -ItemType File -Path $stateFile -Force | Out-Null
}

$loggedSessions = @{}
Get-Content -Path $stateFile -ErrorAction SilentlyContinue | ForEach-Object {
    $line = ([string]$_).Trim()
    if (-not [string]::IsNullOrWhiteSpace($line)) {
        $loggedSessions[$line] = $true
    }
}

Write-MonitorLog -Level 'INFO' -Message (
    "Starting Oragorn sub-agent monitor. interval={0}s recent_window={1}s source={2} pattern={3}" -f $IntervalSeconds, $RecentWindowSeconds, $sessionsDir, $sessionFilePattern
)

while ($true) {
    try {
        $newlyLogged = @()
        $cutoff = (Get-Date).AddSeconds(-$RecentWindowSeconds)

        if (-not (Test-Path -LiteralPath $sessionsDir)) {
            Write-MonitorLog -Level 'WARN' -Message ("Sessions directory not found: {0}" -f $sessionsDir)
        }
        else {
            $recentFiles = Get-ChildItem -Path $sessionsDir -File -Filter $sessionFilePattern -ErrorAction Stop |
                Where-Object { $_.LastWriteTime -ge $cutoff } |
                Sort-Object LastWriteTime

            foreach ($file in $recentFiles) {
                $filename = $file.Name

                if ($loggedSessions.ContainsKey($filename)) {
                    continue
                }

                $summary = "Sub-agent completed: $filename"

                try {
                    & $wrapperScript -Action spawn -Status OK -Summary $summary -ModelId 'gpt-5.3-codex' -SkipBundle
                    $wrapperExit = $LASTEXITCODE
                    if ($wrapperExit -ne 0) {
                        Write-MonitorLog -Level 'ERROR' -Message ("Wrapper failed for {0} with exit code {1}" -f $filename, $wrapperExit)
                        continue
                    }

                    Add-Content -Path $stateFile -Value $filename -Encoding UTF8
                    $loggedSessions[$filename] = $true
                    $newlyLogged += $filename
                    Write-MonitorLog -Level 'INFO' -Message ("Logged sub-agent completion file: {0}" -f $filename)
                }
                catch {
                    Write-MonitorLog -Level 'ERROR' -Message ("Exception logging file {0}: {1}" -f $filename, $_.Exception.Message)
                    continue
                }
            }
        }

        if ($newlyLogged.Count -gt 0) {
            try {
                & $bundleScript -Pipeline oragorn -WindowMinutes 2
                $bundleExit = $LASTEXITCODE
                if ($bundleExit -ne 0) {
                    Write-MonitorLog -Level 'ERROR' -Message ("bundle-run-log failed with exit code {0}" -f $bundleExit)
                }
                else {
                    Write-MonitorLog -Level 'INFO' -Message ("Triggered bundle-run-log for {0} new completion file(s)." -f $newlyLogged.Count)
                }
            }
            catch {
                Write-MonitorLog -Level 'ERROR' -Message ("Exception triggering bundle-run-log: {0}" -f $_.Exception.Message)
            }
        }
    }
    catch {
        Write-MonitorLog -Level 'ERROR' -Message ("Monitor cycle exception: {0}" -f $_.Exception.Message)
    }

    Start-Sleep -Seconds $IntervalSeconds
}
