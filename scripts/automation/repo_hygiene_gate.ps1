[CmdletBinding()]
param(
  [ValidateSet('WARN','FAIL')]
  [string]$Mode = 'WARN',
  [int]$LockStaleMinutes = 60,
  [string]$RepoRoot = '',
  [string]$OragornWorkspacePath = 'C:\Users\Clamps\.openclaw\workspace-oragorn',
  [switch]$NoBanner
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}
Set-Location -LiteralPath $RepoRoot

# Preflight adapter: route Oragorn session dumps out of workspace-oragorn/memory
$routeScript = Join-Path $RepoRoot 'scripts\automation\route_oragorn_session_dumps.ps1'
if (Test-Path -LiteralPath $routeScript) {
  try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $routeScript -OragornWorkspacePath $OragornWorkspacePath | Out-Null
  } catch {
    Write-Warning ('Oragorn session dump routing preflight failed: ' + $_.Exception.Message)
  }
}

function Get-UntrackedPaths {
  $lines = @(git status --porcelain=v1 --untracked-files=all)
  $out = @()
  foreach ($ln in $lines) {
    if ([string]::IsNullOrWhiteSpace($ln)) { continue }
    if ($ln.Length -lt 4) { continue }
    if ($ln.Substring(0,2) -eq '??') {
      $p = $ln.Substring(3).Trim()
      if ($p.StartsWith('"') -and $p.EndsWith('"') -and $p.Length -ge 2) {
        $p = $p.Substring(1, $p.Length - 2)
        $p = $p -replace '\\\\', '\\'
        $p = $p -replace '\\"', '"'
      }
      if (-not [string]::IsNullOrWhiteSpace($p)) {
        $out += ($p -replace '\\','/')
      }
    }
  }
  return @($out | Select-Object -Unique)
}

function Is-AllowedUntrackedPath([string]$PathNorm, [string[]]$AllowPrefixes) {
  foreach ($prefix in $AllowPrefixes) {
    if ($PathNorm.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }
  return $false
}

function Try-ParseJson([string]$RawText) {
  try {
    if ([string]::IsNullOrWhiteSpace($RawText)) { return $null }
    return ($RawText | ConvertFrom-Json)
  } catch {
    return $null
  }
}

function Test-GitTracked([string]$PathNorm) {
  try {
    git ls-files --error-unmatch -- $PathNorm *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Get-LockPid([string]$LockPath) {
  if (-not (Test-Path -LiteralPath $LockPath)) { return $null }
  $raw = ''
  try { $raw = [string](Get-Content -LiteralPath $LockPath -Raw -ErrorAction Stop) } catch { return $null }
  if ([string]::IsNullOrWhiteSpace($raw)) { return $null }

  $obj = Try-ParseJson -RawText $raw
  if ($null -ne $obj) {
    foreach ($k in @('pid','process_id','processId','owner_pid')) {
      if ($obj.PSObject.Properties.Name -contains $k) {
        $v = [string]$obj.$k
        if ($v -match '^\d+$') { return [int]$v }
      }
    }
  }

  if ($raw -match '(?im)\bpid\b\s*[:=]\s*(\d+)') {
    return [int]$matches[1]
  }

  $trim = $raw.Trim()
  if ($trim -match '^\d+$') { return [int]$trim }

  return $null
}

function Test-ProcessExists([int]$ProcId) {
  try {
    $p = Get-Process -Id $ProcId -ErrorAction Stop
    return ($null -ne $p)
  } catch {
    return $false
  }
}

$allowUntrackedPrefixes = @(
  'artifacts/',
  'data/',
  'docs/',
  'memory/'
)

$untracked = Get-UntrackedPaths

$rootLeaks = @()
$otherViolations = @()
$memoryDumpViolations = @()
$backupViolations = @()

foreach ($p in $untracked) {
  $isRoot = ($p -notmatch '/')
  if ($isRoot) {
    $rootLeaks += $p
    continue
  }

  if ($p -match '^memory/\d{4}-\d{2}-\d{2}-.+\.md$') {
    if (-not (Test-GitTracked -PathNorm $p)) {
      $memoryDumpViolations += $p
    }
  }

  if ($p -match '(?i)(\.bak(?:-|\.|$)|\.tmp$|\.orig$|~$|/backup/)') {
    $backupViolations += $p
  }

  if (-not (Is-AllowedUntrackedPath -PathNorm $p -AllowPrefixes $allowUntrackedPrefixes)) {
    $otherViolations += $p
  }
}

# Also detect memory dumps by filesystem pattern (even if ignored), but only when not tracked
$memoryDir = Join-Path $RepoRoot 'memory'
if (Test-Path -LiteralPath $memoryDir) {
  $fsMemoryDumps = @(Get-ChildItem -LiteralPath $memoryDir -File -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^\d{4}-\d{2}-\d{2}-.+\.md$'
  } | ForEach-Object {
    ('memory/' + $_.Name)
  })
  foreach ($md in $fsMemoryDumps) {
    if ((-not (Test-GitTracked -PathNorm $md)) -and ($memoryDumpViolations -notcontains $md)) { $memoryDumpViolations += $md }
  }
}
# Ignore tracked historical memory dumps in this gate; policy applies to new/raw untracked dumps only.
$memoryDumpViolations = @($memoryDumpViolations | Where-Object { -not (Test-GitTracked -PathNorm $_) })

# Stale lock scan (non-destructive)
$staleLocks = @()
$lockCandidates = @()
$stateRoot = Join-Path $RepoRoot 'data\state'
if (Test-Path -LiteralPath $stateRoot) {
  $lockCandidates += @(Get-ChildItem -LiteralPath $stateRoot -Recurse -File -Filter '*.lock' -ErrorAction SilentlyContinue)
}

foreach ($lk in $lockCandidates) {
  $ageMin = [math]::Round(((Get-Date).ToUniversalTime() - $lk.LastWriteTimeUtc).TotalMinutes, 1)
  $ownerPid = Get-LockPid -LockPath $lk.FullName
  $pidRunning = $null
  if ($null -ne $ownerPid) { $pidRunning = Test-ProcessExists -ProcId $ownerPid }

  $isStaleByAge = ($ageMin -gt $LockStaleMinutes)
  $isStaleByPid = (($null -ne $ownerPid) -and ($pidRunning -eq $false))

  if ($isStaleByAge -or $isStaleByPid) {
    $reason = @()
    if ($isStaleByAge) { $reason += ('age>' + $LockStaleMinutes + 'm') }
    if ($isStaleByPid) { $reason += ('owner_pid_not_running=' + $ownerPid) }

    $relPath = $lk.FullName.Replace($RepoRoot, '').TrimStart([char]92,[char]47).Replace('\\','/')
    $staleLocks += [PSCustomObject]@{
      path = $relPath
      age_minutes = $ageMin
      pid = $ownerPid
      pid_running = $pidRunning
      reason = ($reason -join ';')
    }
  }
}

$rootLeaks = @($rootLeaks | Sort-Object -Unique)
$memoryDumpViolations = @($memoryDumpViolations | Sort-Object -Unique)
$backupViolations = @($backupViolations | Sort-Object -Unique)
$otherViolations = @($otherViolations | Sort-Object -Unique)

$autopilotStateLockStale = $false
foreach ($sl in $staleLocks) {
  $p = ([string]$sl.path).Replace('\','/').ToLowerInvariant()
  if ($p -eq 'data/state/autopilot.lock' -or $p -eq 'data/state/locks/autopilot_worker.lock') {
    $autopilotStateLockStale = $true
    break
  }
}

$hasViolations = ($rootLeaks.Count -gt 0 -or $memoryDumpViolations.Count -gt 0 -or $backupViolations.Count -gt 0 -or $otherViolations.Count -gt 0 -or $staleLocks.Count -gt 0)

if (-not $NoBanner) {
  Write-Output ('Repo Hygiene Gate (' + $Mode + ')')
  Write-Output ('Repo: ' + $RepoRoot)
}

Write-Output ''
Write-Output '== Violations Summary =='
Write-Output ('root-leaks: ' + $rootLeaks.Count)
Write-Output ('memory-dumps: ' + $memoryDumpViolations.Count)
Write-Output ('backups: ' + $backupViolations.Count)
Write-Output ('stale-locks: ' + $staleLocks.Count)
Write-Output ('other: ' + $otherViolations.Count)

if ($rootLeaks.Count -gt 0) {
  Write-Output ''
  Write-Output '[root-leaks]'
  foreach ($x in $rootLeaks) { Write-Output ('- ' + $x) }
}

if ($memoryDumpViolations.Count -gt 0) {
  Write-Output ''
  Write-Output '[memory-dumps]'
  foreach ($x in $memoryDumpViolations) { Write-Output ('- ' + $x) }
}

if ($backupViolations.Count -gt 0) {
  Write-Output ''
  Write-Output '[backups]'
  foreach ($x in $backupViolations) { Write-Output ('- ' + $x) }
}

if ($staleLocks.Count -gt 0) {
  Write-Output ''
  Write-Output '[stale-locks]'
  foreach ($x in $staleLocks) {
    Write-Output ('- ' + $x.path + ' | age_min=' + $x.age_minutes + ' | pid=' + $x.pid + ' | pid_running=' + $x.pid_running + ' | reason=' + $x.reason)
  }
  Write-Output ''
  Write-Output 'Remediation (non-destructive):'
  Write-Output '- Confirm no active owner process for each stale lock.'
  Write-Output '- If confirmed safe, remove lock manually (e.g., Remove-Item <lockpath>).' 
  Write-Output '- Re-run hygiene gate before next autopilot cycle.'
}

if ($otherViolations.Count -gt 0) {
  Write-Output ''
  Write-Output '[other]'
  foreach ($x in $otherViolations) { Write-Output ('- ' + $x) }
}

if (-not $hasViolations) {
  Write-Output ''
  Write-Output 'RESULT: CLEAN'
  exit 0
}

if ($Mode -eq 'FAIL') {
  Write-Output ''
  if ($staleLocks.Count -gt 0) {
    if ($autopilotStateLockStale) {
      Write-Output 'RESULT: FAIL (stale lock detected, includes autopilot lock)'
    } else {
      Write-Output 'RESULT: FAIL (stale lock(s) detected)'
    }
  } else {
    Write-Output 'RESULT: FAIL (violations present)'
  }
  exit 2
}

Write-Output ''
Write-Output 'RESULT: WARN (violations present; non-blocking)'
exit 0
