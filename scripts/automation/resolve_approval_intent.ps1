param(
  [Parameter(Mandatory = $true)][string]$Message,
  [string]$BuildSessionId,
  [string]$TaskId
)

$ErrorActionPreference = 'Stop'

function Get-Intent([string]$text) {
  $t = $text.ToLowerInvariant()
  $approve = @('yes','yep','yeah','approve','go ahead','do it','apply it','ship it','looks good','merge it','send it through')
  $reject = @('no','nope','reject',"don't",'stop','cancel','leave it','not yet','hold off')

  foreach ($k in $approve) { if ($t.Contains($k)) { return 'APPROVE' } }
  foreach ($k in $reject) { if ($t.Contains($k)) { return 'REJECT' } }
  return 'UNKNOWN'
}

$intent = Get-Intent $Message
if ($intent -eq 'UNKNOWN') {
  Write-Output 'Approve or reject?'
  exit 3
}

# Build-session path first
$readyBuilds = @()
if (Test-Path 'build_session_ledger.jsonl') {
  $latest = @{}
  Get-Content build_session_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    $obj = $_ | ConvertFrom-Json
    $latest[$obj.build_session_id] = $obj
  }
  $readyBuilds = @($latest.Values | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' })
}

if (-not [string]::IsNullOrWhiteSpace($BuildSessionId)) {
  if ($intent -eq 'APPROVE') {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $BuildSessionId
  } else {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $BuildSessionId
  }
  exit $LASTEXITCODE
}

if ($readyBuilds.Count -gt 1) {
  Write-Output 'Which build?'
  $readyBuilds | Sort-Object last_update_at -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Output ("- " + $_.build_session_id + " | " + $_.description + " | " + $_.last_update_at)
  }
  exit 4
}

if ($readyBuilds.Count -eq 1) {
  $sid = [string]$readyBuilds[0].build_session_id
  if ($intent -eq 'APPROVE') {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid
  } else {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid
  }
  exit $LASTEXITCODE
}

# Fallback to task-level approvals if no build session ready
$readyTasks = @()
if (Test-Path 'task_ledger.jsonl') {
  $latestTask = @{}
  Get-Content task_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    $obj = $_ | ConvertFrom-Json
    $latestTask[$obj.task_id] = $obj
  }
  $readyTasks = @($latestTask.Values | Where-Object { $_.state -eq 'READY_FOR_USER_APPROVAL' })
}

if (-not [string]::IsNullOrWhiteSpace($TaskId)) {
  if ($intent -eq 'APPROVE') {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action APPROVE -TaskId $TaskId
  } else {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action REJECT -TaskId $TaskId
  }
  exit $LASTEXITCODE
}

if ($readyTasks.Count -gt 1) {
  Write-Output 'Which build?'
  $readyTasks | Sort-Object last_update_at -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Output ("- " + $_.task_id + " | " + $_.description + " | " + $_.last_update_at)
  }
  exit 5
}

if ($readyTasks.Count -eq 1) {
  $tid = [string]$readyTasks[0].task_id
  if ($intent -eq 'APPROVE') {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action APPROVE -TaskId $tid
  } else {
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action REJECT -TaskId $tid
  }
  exit $LASTEXITCODE
}

Write-Output 'No approval-ready item found.'
exit 6
