Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'

$lockPath = 'data\state\locks\autopilot_worker.lock'
$workerScript = '.\scripts\pipeline\autopilot_worker.ps1'
$workerTimeoutSeconds = 1500   # 25 minutes hard timeout
$staleLockMinutes = 10
$maxRuntimeMinutes = 30

function Get-AutopilotProcesses {
  try {
    return @(
      Get-CimInstance Win32_Process -ErrorAction Stop |
      Where-Object {
        ($_.Name -match 'powershell') -and (
          ($_.CommandLine -match 'autopilot_worker\.ps1') -or
          ($_.CommandLine -match 'run_autopilot_task\.ps1')
        )
      }
    )
  } catch {
    return @()
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
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    return ([DateTime]::UtcNow - $item.LastWriteTimeUtc).TotalMinutes
  } catch {
    return 0
  }
}

function Kill-AutopilotProcesses {
  $killed = 0
  foreach ($p in @(Get-AutopilotProcesses)) {
    try {
      Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
      $killed++
    } catch {}
  }
  return $killed
}

# Preflight lock recovery to avoid permanent stalls.
if (Test-Path -LiteralPath $lockPath) {
  $lockAgeMin = Get-LockAgeMinutes -Path $lockPath
  $procs = @(Get-AutopilotProcesses)

  if ($procs.Count -eq 0 -and $lockAgeMin -ge $staleLockMinutes) {
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    Write-Host ('Recovered stale lock (no process): age=' + [Math]::Round($lockAgeMin, 1) + 'm')
  } elseif ($procs.Count -gt 0) {
    $oldestProcAgeMin = 0
    foreach ($p in $procs) {
      try {
        $created = [Management.ManagementDateTimeConverter]::ToDateTime([string]$p.CreationDate).ToUniversalTime()
        $age = ([DateTime]::UtcNow - $created).TotalMinutes
        if ($age -gt $oldestProcAgeMin) { $oldestProcAgeMin = $age }
      } catch {}
    }

    if ($lockAgeMin -ge $staleLockMinutes -and $oldestProcAgeMin -ge $maxRuntimeMinutes) {
      $k = Kill-AutopilotProcesses
      Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
      Write-Host ('Recovered hung autopilot: killed=' + $k + ' lock_age=' + [Math]::Round($lockAgeMin,1) + 'm proc_age=' + [Math]::Round($oldestProcAgeMin,1) + 'm')
    } else {
      Write-Host 'Autopilot worker lock/process active; skipping this cycle cleanly.'
      exit 0
    }
  } else {
    Write-Host 'Autopilot worker lock present; skipping this cycle cleanly.'
    exit 0
  }
}

if (-not (Test-Path -LiteralPath $workerScript)) {
  Write-Host ('ERROR: missing worker script: ' + $workerScript)
  exit 1
}

# Run worker in child process with hard timeout so this wrapper cannot hang forever.
$argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $workerScript, '-RepoHygieneMode', 'FAIL')
$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -PassThru -WindowStyle Hidden

if (-not $proc.WaitForExit($workerTimeoutSeconds * 1000)) {
  try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
  Start-Sleep -Milliseconds 300
  $k = Kill-AutopilotProcesses
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
  Write-Host ('ERROR: autopilot worker timeout after ' + $workerTimeoutSeconds + 's; killed=' + $k)
  exit 1
}

$workerExit = [int]$proc.ExitCode
if ($workerExit -ne 0) {
  Write-Host ('ERROR: autopilot worker exit=' + $workerExit)
  # Best-effort cleanup if lock remained after failure and no active process exists.
  if ((Test-Path -LiteralPath $lockPath) -and (@(Get-AutopilotProcesses).Count -eq 0)) {
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

# Hyper mode chain authority is Quandalf -> Frodex (triggered from quandalf-auto-execute.sh).
# Do not trigger Quandalf handoff from Frodex completion here; this causes reversed flow/double logging.
