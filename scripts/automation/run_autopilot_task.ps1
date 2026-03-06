Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'

$lockPath = 'data\state\locks\autopilot_worker.lock'
$workerScript = '.\scripts\pipeline\autopilot_worker.ps1'
$workerTimeoutSeconds = 1500 # 25m hard timeout
$staleLockMinutes = 10

function Get-AutopilotProcessCount {
  try {
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
      ($_.Name -match 'powershell') -and (
        ($_.CommandLine -match 'autopilot_worker\.ps1') -or
        ($_.CommandLine -match 'run_autopilot_task\.ps1')
      )
    }
    return @($procs).Count
  } catch {
    return 0
  }
}

function Get-LockAgeMinutes {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return 0 }
  try {
    $raw = [string](Get-Content -LiteralPath $Path -Raw -ErrorAction Stop)
    if (-not [string]::IsNullOrWhiteSpace($raw)) {
      $ts = [DateTime]::Parse($raw).ToUniversalTime()
      return ([DateTime]::UtcNow - $ts).TotalMinutes
    }
  } catch {}

  try {
    $it = Get-Item -LiteralPath $Path -ErrorAction Stop
    return ([DateTime]::UtcNow - $it.LastWriteTimeUtc).TotalMinutes
  } catch {
    return 0
  }
}

# Recover stale lock when no autopilot process exists.
if (Test-Path -LiteralPath $lockPath) {
  $procCount = Get-AutopilotProcessCount
  $lockAge = Get-LockAgeMinutes -Path $lockPath
  if ($procCount -eq 0 -and $lockAge -ge $staleLockMinutes) {
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    Write-Host ('Recovered stale lock (age=' + [Math]::Round($lockAge,1) + 'm).')
  }
}

if (Test-Path -LiteralPath $lockPath) {
  Write-Host 'Autopilot worker lock present; skipping this cycle cleanly.'
  exit 0
}

if (-not (Test-Path -LiteralPath $workerScript)) {
  Write-Host ('ERROR: missing worker script: ' + $workerScript)
  exit 1
}

# Run worker in child process with timeout to avoid permanent hangs.
$argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $workerScript, '-RepoHygieneMode', 'FAIL')
$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -PassThru -WindowStyle Hidden

if (-not $proc.WaitForExit($workerTimeoutSeconds * 1000)) {
  try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
  Start-Sleep -Milliseconds 250
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
  Write-Host ('ERROR: autopilot worker timeout after ' + $workerTimeoutSeconds + 's')
  exit 1
}

$workerExit = [int]$proc.ExitCode
if ($workerExit -ne 0) {
  Write-Host ('ERROR: autopilot worker exit=' + $workerExit)
  if ((Test-Path -LiteralPath $lockPath) -and ((Get-AutopilotProcessCount) -eq 0)) {
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
  }
  exit $workerExit
}

# Fire the Frodex card immediately after cycle completion (event-driven logging).
try {
  & '.\scripts\automation\bundle-run-log.ps1' -Pipeline frodex -WindowMinutes 16 | Out-Null
} catch {
  Write-Host ('WARN: immediate frodex log send failed: ' + $_.Exception.Message)
}

# Hyper mode: event-chain handoff (Frodex completion -> Quandalf trigger path) without schedule polling.
$hyperMode = $false
try {
  $flagsPath = '.\config\runtime_flags.json'
  if (Test-Path -LiteralPath $flagsPath) {
    $flags = Get-Content -LiteralPath $flagsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($flags -and $flags.PSObject.Properties.Name -contains 'hyperMode') {
      $hyperMode = [bool]$flags.hyperMode
    }
  }
} catch {
  $hyperMode = $false
}

if ($hyperMode) {
  try {
    $latestRunId = ''
    if (Test-Path -LiteralPath '.\data\logs\actions.ndjson') {
      $rows = Get-Content -LiteralPath '.\data\logs\actions.ndjson' -Tail 300 -Encoding UTF8
      foreach ($line in $rows) {
        try { $e = $line | ConvertFrom-Json } catch { continue }
        if ([string]$e.action -ne 'LAB_SUMMARY') { continue }
        $rid = [string]$e.run_id
        if ($rid -match '^(autopilot-\d+)') { $latestRunId = $matches[1] }
      }
    }

    if (-not [string]::IsNullOrWhiteSpace($latestRunId)) {
      & '.\scripts\automation\check_quandalf_handoff.ps1' -RunIdHint $latestRunId | Out-Null
    } else {
      & '.\scripts\automation\check_quandalf_handoff.ps1' | Out-Null
    }
  } catch {
    Write-Host ('WARN: hyper handoff trigger failed: ' + $_.Exception.Message)
  }
}
