[CmdletBinding()]
param(
  [switch]$Apply,
  [switch]$DryRun,
  [switch]$NoStart,
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

function New-V2Action {
  param(
    [string]$Command,
    [string]$RepoRoot
  )

  $escapedRoot = $RepoRoot.Replace("'", "''")
  $escapedCommand = $Command.Replace("'", "''")
  $inner = "Set-Location -LiteralPath '$escapedRoot'; & ([scriptblock]::Create('$escapedCommand'))"
  $bytes = [System.Text.Encoding]::Unicode.GetBytes($inner)
  $encoded = [Convert]::ToBase64String($bytes)
  $arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand ' + $encoded

  return New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $RepoRoot
}

function New-V2Triggers {
  param($Schedule)

  $kind = [string]$Schedule.kind

  if ($kind -eq 'daily') {
    $triggers = @()
    foreach ($time in @($Schedule.times)) {
      $triggers += New-ScheduledTaskTrigger -Daily -At ([string]$time)
    }
    return ,$triggers
  }

  if ($kind -eq 'weekly') {
    $days = @($Schedule.days | ForEach-Object { [string]$_ })
    $time = [string]$Schedule.time
    return @(New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $time)
  }

  if ($kind -eq 'interval') {
    $intervalMinutes = 0
    if ($null -ne $Schedule.minutes) {
      $intervalMinutes = [int]$Schedule.minutes
    }
    elseif ($null -ne $Schedule.hours) {
      $intervalMinutes = [int]$Schedule.hours * 60
    }
    else {
      throw 'Interval schedule requires minutes or hours.'
    }

    if ($intervalMinutes -lt 1) {
      throw 'Interval schedule must be at least 1 minute.'
    }

    $start = (Get-Date).AddMinutes(1)
    $repeatInterval = New-TimeSpan -Minutes $intervalMinutes
    $repeatDuration = New-TimeSpan -Days 3650
    return @(New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval $repeatInterval -RepetitionDuration $repeatDuration)
  }

  throw ('Unsupported schedule kind: ' + $kind)
}

function Convert-IntervalToMinutes {
  param($Interval)

  if ($null -eq $Interval) { return 0 }

  if ($Interval -is [TimeSpan]) {
    return [int][Math]::Round($Interval.TotalMinutes)
  }

  $raw = [string]$Interval
  if ([string]::IsNullOrWhiteSpace($raw)) { return 0 }

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

function Get-LiveCommandArgs {
  param($Task)

  if ($Task.Actions.Count -lt 1) {
    return ''
  }

  return [string]$Task.Actions[0].Arguments
}

$repoRoot = Get-RepoRoot
$resolvedManifest = Resolve-ManifestPath -Path $ManifestPath -RepoRoot $repoRoot

if (-not (Test-Path -LiteralPath $resolvedManifest)) {
  throw ('Manifest not found: ' + $resolvedManifest)
}

if ($Apply -and $DryRun) {
  throw 'Choose either -Apply or -DryRun, not both.'
}

if (-not $Apply -and -not $DryRun) {
  $DryRun = $true
}

$mode = if ($Apply) { 'APPLY' } else { 'DRYRUN' }
Write-Host ('[V2 Installer] Mode=' + $mode + ' Manifest=' + $resolvedManifest)

$manifestRaw = Get-Content -LiteralPath $resolvedManifest -Raw
$manifest = $manifestRaw | ConvertFrom-Json
$version = [string]$manifest.version
$tasks = @($manifest.tasks | Where-Object { [string]$_.type -eq 'task' })

$settings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

$created = 0
$updated = 0
$unchanged = 0

foreach ($taskEntry in $tasks) {
  $taskName = [string]$taskEntry.name
  $owner = [string]$taskEntry.owner
  $command = [string]$taskEntry.command
  $desiredScheduleShape = Get-DesiredScheduleShape -Schedule $taskEntry.schedule
  $desiredAction = New-V2Action -Command $command -RepoRoot $repoRoot
  $desiredArgs = [string]$desiredAction.Arguments
  $description = ('automation_v2 owner=' + $owner + ';version=' + $version)

  $existing = $null
  try {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  }
  catch {
    $existing = $null
  }

  $needsChange = $true
  $reason = ''

  if ($null -eq $existing) {
    $reason = 'missing'
  }
  else {
    $liveScheduleShape = Get-LiveScheduleShape -Task $existing
    $liveArgs = Get-LiveCommandArgs -Task $existing

    $argsMatch = ($liveArgs -eq $desiredArgs)
    $scheduleMatch = ($liveScheduleShape -eq $desiredScheduleShape)

    if ($argsMatch -and $scheduleMatch) {
      $needsChange = $false
      $reason = 'up-to-date'
    }
    else {
      $diff = @()
      if (-not $scheduleMatch) { $diff += ('schedule ' + $liveScheduleShape + ' -> ' + $desiredScheduleShape) }
      if (-not $argsMatch) { $diff += 'command args differ' }
      $reason = ($diff -join '; ')
    }
  }

  if (-not $needsChange) {
    $unchanged++
    Write-Host ('[SKIP] ' + $taskName + ' (' + $reason + ')')
    continue
  }

  $triggers = New-V2Triggers -Schedule $taskEntry.schedule

  if ($Apply) {
    Register-ScheduledTask -TaskName $taskName -Action $desiredAction -Trigger $triggers -Settings $settings -Description $description -Force | Out-Null
    if ($null -eq $existing) {
      $created++
      Write-Host ('[CREATE] ' + $taskName + ' (' + $reason + ')')
    }
    else {
      $updated++
      Write-Host ('[UPDATE] ' + $taskName + ' (' + $reason + ')')
    }
  }
  else {
    $tag = if ($null -eq $existing) { 'PLAN-CREATE' } else { 'PLAN-UPDATE' }
    Write-Host ('[' + $tag + '] ' + $taskName + ' (' + $reason + ')')
  }
}

if ($NoStart) {
  Write-Host '[INFO] -NoStart set: installer does not start tasks in this phase.'
}

Write-Host ('[SUMMARY] created=' + $created + ' updated=' + $updated + ' unchanged=' + $unchanged + ' total=' + $tasks.Count + ' mode=' + $mode)
