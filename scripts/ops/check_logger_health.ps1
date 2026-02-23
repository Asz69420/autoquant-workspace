param(
  [int]$FreshDrainMinutes = 10,
  [int]$SpawnLookbackMinutes = 120,
  [switch]$Strict
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $workspace

$failures = @()

function Add-Fail($msg) { $script:failures += $msg }

# 1) task exists/enabled + restart policy
$task = Get-ScheduledTask -TaskName 'AutoQuant-tg_reporter' -ErrorAction SilentlyContinue
if (-not $task) {
  Add-Fail 'AutoQuant-tg_reporter task missing'
} else {
  if ($task.State -eq 'Disabled') { Add-Fail 'AutoQuant-tg_reporter task disabled' }
  $xml = [xml](Export-ScheduledTask -TaskName 'AutoQuant-tg_reporter')
  $restart = $xml.Task.Settings.RestartOnFailure
  if (-not $restart -or -not $restart.Interval -or -not $restart.Count) {
    Add-Fail 'RestartOnFailure policy missing on AutoQuant-tg_reporter'
  }
}

# 2) active/recoverable
$p = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Python314*' }
if (-not $p) {
  Add-Fail 'No python process detected for tg_reporter (not running)'
}

# 3) drain freshness + stale outbox
$actions = Join-Path $workspace 'data\logs\actions.ndjson'
if (-not (Test-Path $actions)) {
  Add-Fail 'actions.ndjson missing'
} else {
  $tail = @(Get-Content $actions -Tail 300)
  $lastTg = $null
  for ($i = $tail.Count - 1; $i -ge 0; $i--) {
    $line = $tail[$i]
    if ($line -match '"ts_iso"\s*:\s*"([^"]+)"') {
      $lastTg = [datetime]::Parse($Matches[1]).ToUniversalTime(); break
    }
  }
  if (-not $lastTg) {
    Add-Fail 'Could not parse last ts_iso in actions.ndjson'
  } else {
    $age = ((Get-Date).ToUniversalTime() - $lastTg).TotalMinutes
    if ($age -gt $FreshDrainMinutes) {
      Add-Fail ("actions.ndjson appears stale ({0:N1}m > {1}m)" -f $age,$FreshDrainMinutes)
    }
  }
}

$outbox = Join-Path $workspace 'data\logs\outbox'
if (Test-Path $outbox) {
  $stale = Get-ChildItem $outbox -File -ErrorAction SilentlyContinue | Where-Object { ((Get-Date) - $_.LastWriteTime).TotalMinutes -gt $FreshDrainMinutes }
  if ($stale.Count -gt 0) {
    Add-Fail ("stale outbox files detected: {0}" -f $stale.Count)
  }
}

# 4) recent spawn terminal coverage (strict reconcile)
$py = Join-Path $workspace 'scripts\spawn_lifecycle_reconcile.py'
if (Test-Path $py) {
  python scripts/spawn_lifecycle_reconcile.py --strict --grace-seconds 120 --require-actions-log --max-age-minutes $SpawnLookbackMinutes | Out-Null
  if ($LASTEXITCODE -ne 0) {
    # one retry after a manual drain to avoid transient outbox->actions race
    python scripts/tg_reporter.py --manual | Out-Null
    python scripts/spawn_lifecycle_reconcile.py --strict --grace-seconds 120 --require-actions-log --max-age-minutes $SpawnLookbackMinutes | Out-Null
    if ($LASTEXITCODE -ne 0) {
      Add-Fail 'spawn lifecycle reconcile strict failed'
    }
  }
} else {
  Add-Fail 'spawn_lifecycle_reconcile.py missing'
}

if ($failures.Count -gt 0) {
  Write-Output '❌ LOGGER HEALTH: FAIL'
  $failures | ForEach-Object { Write-Output ("- " + $_) }
  exit 2
}

Write-Output '✅ LOGGER HEALTH: PASS'
exit 0
