param(
  [Parameter(Mandatory = $true)][string]$Message,
  [string]$BuildSessionId,
  [string]$TaskId,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Emit-LogEvent {
  param(
    [string]$RunId,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary,
    [string[]]$Outputs
  )
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','request_router','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  python @args 2>$null | Out-Null
}

function Get-Intent([string]$text) {
  $t = $text.ToLowerInvariant()
  $approve = @('yes','yep','yeah','approve','go ahead','do it','apply','okay apply','apply it','ship it','looks good','merge it','send it through')
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
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $BuildSessionId -DryRun
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $BuildSessionId
    }
  } else {
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $BuildSessionId -DryRun
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $BuildSessionId
    }
  }
  exit $LASTEXITCODE
}

if ($DryRun -and $readyBuilds.Count -eq 0 -and [string]::IsNullOrWhiteSpace($BuildSessionId)) {
  Emit-LogEvent -RunId ("approval-intent-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + "-dryrun") -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - no pending approvals' -Outputs @('no_pending_approvals')
  Write-Output 'Dry run — no pending approvals.'
  exit 0
}

if ($readyBuilds.Count -ge 1) {
  $sorted = $readyBuilds | Sort-Object last_update_at -Descending
  $sid = [string]$sorted[0].build_session_id
  if ($intent -eq 'APPROVE') {
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would apply the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid | Out-Null
      Write-Output 'Done — applied the latest ready build.'
    }
  } else {
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would reject the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid | Out-Null
      Write-Output 'Done — rejected the latest ready build.'
    }
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
