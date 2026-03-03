[CmdletBinding()]
param(
  [string]$ManifestPath
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
  $scriptsDir = Split-Path -Parent $PSScriptRoot
  return (Split-Path -Parent $scriptsDir)
}

function Resolve-ManifestPath {
  param(
    [string]$Path,
    [string]$RepoRoot
  )

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return (Join-Path $RepoRoot 'config\automation_v2_manifest.json')
  }

  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }

  return (Join-Path $RepoRoot $Path)
}

function Get-DesiredScheduleShape {
  param($Schedule)

  $kind = [string]$Schedule.kind
  if ($kind -eq 'daily') {
    $times = @($Schedule.times | ForEach-Object { [string]$_ } | Sort-Object)
    return ('daily:' + ($times -join ','))
  }

  if ($kind -eq 'weekly') {
    $days = @($Schedule.days | ForEach-Object { [string]$_ } | Sort-Object)
    $time = [string]$Schedule.time
    return ('weekly:' + ($days -join ',') + '@' + $time)
  }

  if ($kind -eq 'interval') {
    if ($null -ne $Schedule.minutes) {
      return ('interval:' + [int]$Schedule.minutes + 'm')
    }

    if ($null -ne $Schedule.hours) {
      return ('interval:' + [int]$Schedule.hours + 'h')
    }

    throw 'Interval schedule requires minutes or hours.'
  }

  throw ('Unsupported schedule kind: ' + $kind)
}

function Get-DesiredActionArgs {
  param(
    [string]$Command,
    [string]$RepoRoot
  )

  $escapedRoot = $RepoRoot.Replace("'", "''")
  $escapedCommand = $Command.Replace("'", "''")
  $inner = "Set-Location -LiteralPath '$escapedRoot'; & ([scriptblock]::Create('$escapedCommand'))"
  $bytes = [System.Text.Encoding]::Unicode.GetBytes($inner)
  $encoded = [Convert]::ToBase64String($bytes)
  return ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand ' + $encoded)
}

function Convert-IntervalToMinutes {
  param($Interval)

  if ($null -eq $Interval) { return 0 }

  if ($Interval -is [TimeSpan]) {
    return [int][Math]::Round($Interval.TotalMinutes)
  }

  $raw = [string]$Interval
  if ([string]::IsNullOrWhiteSpace($raw)) { return 0 }

  # ISO8601 duration like PT15M / PT2H
  $m = [regex]::Match($raw, '^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$')
  if ($m.Success) {
    $h = if ($m.Groups[1].Success) { [int]$m.Groups[1].Value } else { 0 }
    $mi = if ($m.Groups[2].Success) { [int]$m.Groups[2].Value } else { 0 }
    $s = if ($m.Groups[3].Success) { [int]$m.Groups[3].Value } else { 0 }
    return [int]([Math]::Floor(($h * 60) + $mi + ($s / 60.0)))
  }

  return 0
}

function Normalize-WeekdayToken {
  param($Token)
  $v = [string]$Token
  switch ($v.ToLowerInvariant()) {
    '0' { return 'Sunday' }
    '1' { return 'Sunday' }
    '2' { return 'Monday' }
    '3' { return 'Tuesday' }
    '4' { return 'Wednesday' }
    '5' { return 'Thursday' }
    '6' { return 'Friday' }
    '7' { return 'Saturday' }
    'sunday' { return 'Sunday' }
    'monday' { return 'Monday' }
    'tuesday' { return 'Tuesday' }
    'wednesday' { return 'Wednesday' }
    'thursday' { return 'Thursday' }
    'friday' { return 'Friday' }
    'saturday' { return 'Saturday' }
    default { return $v }
  }
}

function Get-LiveScheduleShape {
  param($Task)

  $triggers = @($Task.Triggers)
  if ($triggers.Count -eq 0) {
    return 'none'
  }

  $first = $triggers[0]
  if ($null -ne $first.Repetition -and $null -ne $first.Repetition.Interval) {
    $minutes = Convert-IntervalToMinutes -Interval $first.Repetition.Interval
    if ($minutes -gt 0) {
      if ($minutes % 60 -eq 0) {
        return ('interval:' + [int]($minutes / 60) + 'h')
      }
      return ('interval:' + $minutes + 'm')
    }
  }

  if ($null -ne $first.WeeksInterval -and [int]$first.WeeksInterval -gt 0) {
    $days = @()
    foreach ($t in $triggers) {
      if ($null -ne $t.DaysOfWeek) {
        foreach ($d in @($t.DaysOfWeek)) {
          $days += (Normalize-WeekdayToken -Token $d)
        }
      }
    }
    $uniqueDays = @($days | Sort-Object -Unique)
    $time = ([datetime]$first.StartBoundary).ToString('HH:mm')
    return ('weekly:' + ($uniqueDays -join ',') + '@' + $time)
  }

  if ($null -ne $first.DaysInterval -and [int]$first.DaysInterval -gt 0) {
    $times = @()
    foreach ($t in $triggers) {
      $times += ([datetime]$t.StartBoundary).ToString('HH:mm')
    }
    $uniqueTimes = @($times | Sort-Object -Unique)
    return ('daily:' + ($uniqueTimes -join ','))
  }

  # fallback: if multiple time triggers with no repetition/week markers, treat as daily times
  $times = @()
  foreach ($t in $triggers) {
    if ($null -ne $t.StartBoundary) {
      $times += ([datetime]$t.StartBoundary).ToString('HH:mm')
    }
  }
  if ($times.Count -gt 0) {
    $uniqueTimes = @($times | Sort-Object -Unique)
    return ('daily:' + ($uniqueTimes -join ','))
  }

  return 'unknown'
}

$repoRoot = Get-RepoRoot
$resolvedManifest = Resolve-ManifestPath -Path $ManifestPath -RepoRoot $repoRoot

if (-not (Test-Path -LiteralPath $resolvedManifest)) {
  throw ('Manifest not found: ' + $resolvedManifest)
}

$manifestRaw = Get-Content -LiteralPath $resolvedManifest -Raw
$manifest = $manifestRaw | ConvertFrom-Json
$tasks = @($manifest.tasks | Where-Object { [string]$_.type -eq 'task' })

$passCount = 0
$warnCount = 0
$failCount = 0

foreach ($taskEntry in $tasks) {
  $name = [string]$taskEntry.name
  $owner = [string]$taskEntry.owner
  $expectedSchedule = Get-DesiredScheduleShape -Schedule $taskEntry.schedule
  $expectedArgs = Get-DesiredActionArgs -Command ([string]$taskEntry.command) -RepoRoot $repoRoot

  $task = $null
  try {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
  }
  catch {
    $task = $null
  }

  if ($null -eq $task) {
    $failCount++
    Write-Host ('FAIL ' + $name + ' :: missing scheduled task')
    continue
  }

  $issues = @()
  $warnings = @()

  if ([string]$task.Actions[0].Execute -ne 'powershell.exe') {
    $issues += ('execute=' + [string]$task.Actions[0].Execute + ' expected=powershell.exe')
  }

  $liveArgs = [string]$task.Actions[0].Arguments
  if ($liveArgs -ne $expectedArgs) {
    $issues += 'command args mismatch'
  }

  $liveSchedule = Get-LiveScheduleShape -Task $task
  if ($liveSchedule -ne $expectedSchedule) {
    $issues += ('schedule=' + $liveSchedule + ' expected=' + $expectedSchedule)
  }

  $desc = [string]$task.Description
  if ($desc -match 'owner=([^;\s]+)') {
    $liveOwner = $Matches[1]
    if ($liveOwner -ne $owner) {
      $issues += ('owner=' + $liveOwner + ' expected=' + $owner)
    }
  }
  else {
    $warnings += 'owner metadata missing in description'
  }

  if ($issues.Count -gt 0) {
    $failCount++
    Write-Host ('FAIL ' + $name + ' :: ' + ($issues -join '; '))
    continue
  }

  if ($warnings.Count -gt 0) {
    $warnCount++
    Write-Host ('WARN ' + $name + ' :: ' + ($warnings -join '; '))
    continue
  }

  $passCount++
  Write-Host ('PASS ' + $name)
}

Write-Host ('SUMMARY PASS=' + $passCount + ' WARN=' + $warnCount + ' FAIL=' + $failCount + ' TOTAL=' + $tasks.Count)
if ($failCount -gt 0) {
  exit 1
}
