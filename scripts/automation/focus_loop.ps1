param(
  [Parameter(Mandatory=$true, Position=0)]
  [ValidateSet('start','stop','list')]
  [string]$Action,

  [string]$Name,
  [string]$Every = '15m',
  [string]$Task,
  [string]$Agent = 'main'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Require-Value([string]$Value, [string]$Field) {
  if ([string]::IsNullOrWhiteSpace($Value)) {
    throw "Missing required --$Field"
  }
}

function Get-CronJobs {
  $json = openclaw cron list --json
  return ($json | ConvertFrom-Json).jobs
}

function Find-FocusJobByName([string]$BaseName) {
  $jobName = "focus-$BaseName"
  $jobs = Get-CronJobs
  return $jobs | Where-Object { $_.name -eq $jobName }
}

switch ($Action) {
  'start' {
    Require-Value $Name 'name'
    Require-Value $Task 'task'

    $existing = Find-FocusJobByName $Name
    if ($existing) {
      throw "Focus loop already exists: focus-$Name (id: $($existing[0].id))"
    }

    $message = @"
FOCUS LOOP TASK: $Task

Instructions:
- Continue progressing this task in small, concrete increments each run.
- Read prior outputs/logs first; resume from last known state.
- If task is finished: reply "FOCUS_DONE: <summary>".
- If blocked by a true dependency or missing decision: reply "FOCUS_BLOCKED: <what you need>".
- If neither done nor blocked: do meaningful progress and summarize briefly.
- Keep outputs concise and pointer-based; avoid context bloat.
"@

    openclaw cron add `
      --name "focus-$Name" `
      --description "Focus loop for: $Task" `
      --every $Every `
      --agent $Agent `
      --session isolated `
      --message $message `
      --announce

    Write-Output "Started focus loop: focus-$Name (every $Every)"
  }

  'stop' {
    Require-Value $Name 'name'
    $job = Find-FocusJobByName $Name
    if (-not $job) {
      throw "No focus loop found: focus-$Name"
    }

    $id = $job[0].id
    openclaw cron disable --id $id | Out-Null
    openclaw cron rm --id $id | Out-Null
    Write-Output "Stopped focus loop: focus-$Name (id: $id)"
  }

  'list' {
    $jobs = Get-CronJobs | Where-Object { $_.name -like 'focus-*' }
    if (-not $jobs -or $jobs.Count -eq 0) {
      Write-Output 'No focus loops found.'
      break
    }

    foreach ($j in $jobs) {
      $schedule = if ($j.schedule.kind -eq 'interval') { "every $($j.schedule.everyMs)ms" } else { "$($j.schedule.kind) $($j.schedule.expr)" }
      $status = if ($j.enabled) { 'enabled' } else { 'disabled' }
      Write-Output ("{0} | {1} | {2} | {3}" -f $j.id, $j.name, $status, $schedule)
    }
  }
}
