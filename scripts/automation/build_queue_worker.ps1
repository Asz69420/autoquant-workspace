param(
  [int]$StaleHeartbeatSeconds = 300
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

. "$PSScriptRoot/build_queue_lib.ps1"

function Emit-LogEvent {
  param(
    [string]$RunId,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary,
    [string[]]$Inputs,
    [string[]]$Outputs
  )
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','build_queue_worker','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Inputs) { foreach($i in $Inputs){ $args += @('--inputs',$i) } }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  python @args 2>$null | Out-Null
  $ErrorActionPreference = $oldEap
}

function Send-MainChatNotice {
  param([string]$ChatId,[string]$Text,[string]$MessageId)
  if ([string]::IsNullOrWhiteSpace($ChatId)) { return $false }
  try {
    if ([string]::IsNullOrWhiteSpace($MessageId)) {
      openclaw message send --channel telegram --target $ChatId --message $Text | Out-Null
    } else {
      openclaw message send --channel telegram --target $ChatId --message $Text --reply-to $MessageId | Out-Null
    }
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Emit-MissingChatTargetWarn {
  param([string]$RunId,[string]$JobId,[string]$BuildSessionId,[string]$TaskId)
  Emit-LogEvent -RunId $RunId -StatusWord 'WARN' -StatusEmoji 'WARN' -ReasonCode 'QUEUE_MISSING_CHAT_TARGET' -Summary 'Missing/invalid chat target; user notify skipped; logs only' -Inputs @($JobId) -Outputs @($BuildSessionId,$TaskId)
}

function Get-LatestTaskState {
  param([string]$TaskId)
  if ([string]::IsNullOrWhiteSpace($TaskId) -or -not (Test-Path 'task_ledger.jsonl')) { return '' }
  $latest = ''
  Get-Content task_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    try { $o = $_ | ConvertFrom-Json } catch { return }
    if ($o.task_id -eq $TaskId) { $latest = [string]$o.state }
  }
  return $latest
}

$runId = 'queue-worker-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$lock = Acquire-QueueLock
if (-not $lock.Acquired) {
  if ($lock.Stale) {
    Emit-LogEvent -RunId $runId -StatusWord 'WARN' -StatusEmoji 'WARN' -ReasonCode 'WORKER_STALE_ACTIVE' -Summary 'Queue lock stale; fail-closed until reconciled' -Inputs @() -Outputs @('lock_stale')
  }
  exit 0
}

try {
  $state = Load-QueueState
  Update-QueueLockHeartbeat

  if ($state.active) {
    $active = $state.active
    $hbAt = $null
    try { $hbAt = [DateTimeOffset]::Parse([string]$active.last_heartbeat) } catch { $hbAt = [DateTimeOffset]::MinValue }
    $hbAge = ([DateTimeOffset]::UtcNow - $hbAt).TotalSeconds

    $taskState = Get-LatestTaskState -TaskId ([string]$active.task_id)
    if ($taskState -in @('READY_FOR_USER_APPROVAL','BLOCKED','APPLIED','COMPLETE')) {
      $result = if ($taskState -eq 'READY_FOR_USER_APPROVAL') { 'READY' } elseif ($taskState -eq 'APPLIED') { 'APPLIED' } elseif ($taskState -eq 'COMPLETE') { 'READY' } else { 'BLOCKED' }
      $hist = @($state.history)
      $hist += [ordered]@{ job_id = $active.job_id; result = $result; ended_at = ([DateTimeOffset]::UtcNow.ToString('o')) }
      $state.history = $hist | Select-Object -Last 100
      $state.active = $null
      Save-QueueState -State $state
    } elseif ($hbAge -gt $StaleHeartbeatSeconds) {
      Emit-LogEvent -RunId $runId -StatusWord 'WARN' -StatusEmoji 'WARN' -ReasonCode 'WORKER_STALE_ACTIVE' -Summary ('Stale active job cleared: ' + $active.job_id) -Inputs @($active.job_id) -Outputs @('cleared_active')
      $hist = @($state.history)
      $hist += [ordered]@{ job_id = $active.job_id; result = 'BLOCKED'; ended_at = ([DateTimeOffset]::UtcNow.ToString('o')) }
      $state.history = $hist | Select-Object -Last 100
      $state.active = $null
      Save-QueueState -State $state
    } else {
      $state.active.last_heartbeat = ([DateTimeOffset]::UtcNow.ToString('o'))
      $state.active.worker_pid = "$PID"
      Save-QueueState -State $state
      exit 0
    }
  }

  $dq = Dequeue-NextJob
  $job = $dq.Job
  if ($null -eq $job) { exit 0 }

  $buildStart = python scripts/automation/build_session.py start --description $job.question --force-new
  $buildObj = $buildStart | ConvertFrom-Json
  $buildSessionId = [string]$buildObj.build_session_id
  $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
  $rand = ([guid]::NewGuid().ToString('N')).Substring(0,6)
  $taskId = "$buildSessionId-task-$ts-$rand"

  $state = Load-QueueState
  $state.active = [ordered]@{
    job_id = $job.job_id
    question = $job.question
    created_at = $job.created_at
    started_at = ([DateTimeOffset]::UtcNow.ToString('o'))
    chat_id = $job.chat_id
    message_id = $job.message_id
    update_id = $job.update_id
    idem_key = $job.idem_key
    executor_type = $job.executor_type
    task_id = $taskId
    build_session_id = $buildSessionId
    worker_pid = "$PID"
    last_heartbeat = ([DateTimeOffset]::UtcNow.ToString('o'))
  }
  Save-QueueState -State $state

  Emit-LogEvent -RunId $runId -StatusWord 'INFO' -StatusEmoji 'INFO' -ReasonCode 'BUILD_STARTED' -Summary ('Build started: ' + $job.job_id) -Inputs @($job.question) -Outputs @($taskId, $buildSessionId)

  $runOut = @()
  try {
    $runOut = powershell -ExecutionPolicy Bypass -File scripts/automation/run_work.ps1 -Question $job.question -TaskId $taskId -BuildSessionId $buildSessionId -ExecutorType ([string]$job.executor_type) *>&1
  } catch {
    $runOut = @([string]$_.Exception.Message)
  }

  $text = ($runOut | Out-String)
  $taskState = Get-LatestTaskState -TaskId $taskId

  if ($taskState -eq 'READY_FOR_USER_APPROVAL' -or $text -match 'Build ready for your review') {
    Emit-LogEvent -RunId $runId -StatusWord 'INFO' -StatusEmoji 'INFO' -ReasonCode 'BUILD_READY_FOR_APPROVAL' -Summary ('Build ready: ' + $job.job_id) -Inputs @($taskId) -Outputs @($buildSessionId)
    $notified = Send-MainChatNotice -ChatId ([string]$job.chat_id) -Text 'Build ready for your review. Apply these changes?' -MessageId ([string]$job.message_id)
    if (-not $notified) { Emit-MissingChatTargetWarn -RunId $runId -JobId ([string]$job.job_id) -BuildSessionId $buildSessionId -TaskId $taskId }
    $result = 'READY'
  } else {
    Emit-LogEvent -RunId $runId -StatusWord 'WARN' -StatusEmoji 'WARN' -ReasonCode 'BUILD_BLOCKED' -Summary ('Build blocked: ' + $job.job_id) -Inputs @($taskId) -Outputs @('blocked')
    $notified = Send-MainChatNotice -ChatId ([string]$job.chat_id) -Text "Blocked - could not pass verification within limits. Say 'show debug' for details." -MessageId ([string]$job.message_id)
    if (-not $notified) { Emit-MissingChatTargetWarn -RunId $runId -JobId ([string]$job.job_id) -BuildSessionId $buildSessionId -TaskId $taskId }
    $result = 'BLOCKED'
  }

  $state = Load-QueueState
  $hist = @($state.history)
  $hist += [ordered]@{ job_id = $job.job_id; result = $result; ended_at = ([DateTimeOffset]::UtcNow.ToString('o')) }
  $state.history = $hist | Select-Object -Last 100
  $state.active = $null
  Save-QueueState -State $state
}
finally {
  Release-QueueLock
}
