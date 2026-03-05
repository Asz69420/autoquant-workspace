param()

$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location -LiteralPath $ROOT

$runtimeFlagsPath = Join-Path $ROOT 'config\runtime_flags.json'
$lockPath = Join-Path $ROOT 'data\state\locks\autopilot_worker.lock'

$hyperMode = $false
try {
  if (Test-Path -LiteralPath $runtimeFlagsPath) {
    $flags = Get-Content -LiteralPath $runtimeFlagsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($flags -and $flags.PSObject.Properties.Name -contains 'hyperMode') {
      $hyperMode = [bool]$flags.hyperMode
    }
  }
} catch {
  $hyperMode = $false
}

if (-not $hyperMode) {
  Write-Host 'Skip: hyper mode disabled.'
  exit 0
}

if (Test-Path -LiteralPath $lockPath) {
  Write-Host 'Skip: autopilot worker lock present.'
  exit 0
}

$running = $false
try {
  $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    ($_.Name -match 'powershell') -and (
      ($_.CommandLine -match 'autopilot_worker\.ps1') -or
      ($_.CommandLine -match 'run_autopilot_task\.ps1')
    )
  }
  $running = (@($procs).Count -gt 0)
} catch {
  $running = $false
}

if ($running) {
  Write-Host 'Skip: autopilot process still running.'
  exit 0
}

$taskName = '\frodex-ops-loop-15m'
try {
  schtasks /Run /TN $taskName | Out-Null
  Write-Host 'Triggered: frodex-ops-loop-15m'
} catch {
  # Fallback if scheduler trigger path is unavailable.
  Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File', (Join-Path $ROOT 'scripts\automation\run_autopilot_task.ps1')) -WorkingDirectory $ROOT -WindowStyle Hidden | Out-Null
  Write-Host 'Triggered: run_autopilot_task.ps1 fallback'
}
