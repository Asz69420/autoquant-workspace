param(
  [Parameter(Mandatory = $true)][string]$Message,
  [string]$UpdateId,
  [string]$MessageId,
  [string]$ChatId,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$IdemPath = 'data/state/ingress_idempotency.json'
$IdemTtlSec = 600

. "$PSScriptRoot/build_queue_lib.ps1"

function Get-IdempotencyKey {
  if (-not [string]::IsNullOrWhiteSpace($UpdateId)) { return ('tg:update:' + $UpdateId) }
  if (-not [string]::IsNullOrWhiteSpace($MessageId) -and -not [string]::IsNullOrWhiteSpace($ChatId)) { return ('tg:msg:' + $ChatId + ':' + $MessageId) }
  $bucket = [int]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() / 60)
  $chatPart = if ([string]::IsNullOrWhiteSpace($ChatId)) { '' } else { $ChatId }
  $raw = ($chatPart + '|' + $Message + '|' + $bucket)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
  $hash = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
  return ('fallback:' + $hash)
}

function Should-SkipByIdempotency {
  param([string]$Key)
  $dir = Split-Path -Parent $IdemPath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $cache = @{}
  if (Test-Path $IdemPath) {
    try {
      $raw = Get-Content $IdemPath -Raw
      if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $obj = ConvertFrom-Json $raw
        foreach ($p in $obj.PSObject.Properties) { $cache[$p.Name] = [int64]$p.Value }
      }
    } catch { $cache = @{} }
  }

  # GC expired
  $alive = @{}
  foreach ($k in $cache.Keys) {
    $ts = [int64]$cache[$k]
    if (($now - $ts) -lt $IdemTtlSec) { $alive[$k] = $ts }
  }

  $skip = $false
  if ($alive.ContainsKey($Key)) {
    $skip = $true
  } else {
    $alive[$Key] = $now
  }

  ($alive | ConvertTo-Json -Depth 4) | Set-Content -Path $IdemPath -Encoding utf8
  return $skip
}

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
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','request_router','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Inputs) { foreach($i in $Inputs){ $args += @('--inputs',$i) } }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  python @args 2>$null | Out-Null
  $ErrorActionPreference = $oldEap
}

function Get-LatestReadyBuildId {
  if (-not (Test-Path 'build_session_ledger.jsonl')) { return '' }
  $latest = @{}
  Get-Content build_session_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    $o = $_ | ConvertFrom-Json
    $latest[$o.build_session_id] = $o
  }
  $ready = @($latest.Values | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' } | Sort-Object last_update_at -Descending)
  if ($ready.Count -eq 0) { return '' }
  return [string]$ready[0].build_session_id
}

function Ensure-RuntimeFlags {
  $dir = 'config'
  $path = 'config/runtime_flags.json'
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  if (-not (Test-Path $path)) {
    Set-Content -Path $path -Value '{"warningsEnabled": true}' -Encoding utf8
  }
  return $path
}

# Deterministic routing rules (verbatim)
# FAST_PATH allowed actions (exact):
# - toggle a boolean setting / switch (enable/disable a feature flag)
# - read-only status queries (show pending builds, show latest status, show logs summary)
# - apply latest ready build / reject latest ready build
# - show help / usage
# - show debug/details (read artifacts/ledgers only)
# BUILD_PATH triggered when any are true:
# - user asks to build / implement / patch / update / add feature / refactor
# - request would modify code/files/config other than config/runtime_flags.json
# - request creates new files outside tests/docs
# Default on uncertainty: BUILD_PATH

$m = $Message.ToLowerInvariant()
$debugOverride = ($m.Contains('show debug') -or $m.Contains('details'))
$route = 'BUILD_PATH'
$rule = 'default_unsure_to_build'

function Write-MainChatFiltered {
  param([string[]]$Lines,[bool]$Debug)
  foreach ($ln in $Lines) {
    $s = [string]$ln
    if ([string]::IsNullOrWhiteSpace($s)) { continue }
    if ($Debug) { Write-Output $s; continue }
    if ($s -match '(^\s*\{)|(^\s*\[)|run_id|reason_code|route=|FAST_PATH|BUILD_PATH|taskId=|build_session_id=|model_id|artifacts/|verifier-run:|^Emitted:') { continue }
    Write-Output $s
  }
}

$buildVerbs = @('build','implement','patch','update','add feature','refactor')
$fastStatus = @('show pending builds','any builds waiting for approval','builds waiting for approval','show latest status','show logs summary','show debug','details','help','usage','queue status','cancel next','clear queue')
$fastApply = @('apply latest','reject latest')
$toggleWarnOff = @('turn warnings off','disable warnings','warnings off')
$toggleWarnOn = @('turn warnings on','enable warnings','warnings on')

if ($toggleWarnOff | Where-Object { $m.Contains($_) }) {
  $route = 'FAST_PATH'; $rule = 'toggle_boolean_setting'
} elseif ($toggleWarnOn | Where-Object { $m.Contains($_) }) {
  $route = 'FAST_PATH'; $rule = 'toggle_boolean_setting'
} elseif ($fastApply | Where-Object { $m.Contains($_) }) {
  $route = 'FAST_PATH'; $rule = 'apply_or_reject_latest_ready_build'
} elseif ($fastStatus | Where-Object { $m.Contains($_) }) {
  $route = 'FAST_PATH'; $rule = 'read_only_query_or_help'
} elseif ($buildVerbs | Where-Object { $m.Contains($_) }) {
  $route = 'BUILD_PATH'; $rule = 'explicit_build_intent'
}

$idemKey = Get-IdempotencyKey
if (Should-SkipByIdempotency -Key $idemKey) {
  $skipRunId = 'route-skip-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  Emit-LogEvent -RunId $skipRunId -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'IDEMPOTENT_SKIP' -Summary 'Duplicate ingress message skipped' -Inputs @($idemKey) -Outputs @('SKIPPED')
  Write-Output 'Done — duplicate message ignored.'
  exit 0
}

$runId = 'route-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Emit-LogEvent -RunId $runId -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'ROUTE_DECISION' -Summary ("route=" + $route + "; rule=" + $rule) -Inputs @($Message) -Outputs @($route)

if ($route -eq 'FAST_PATH') {
  if ($toggleWarnOff | Where-Object { $m.Contains($_) }) {
    $f = 'config/runtime_flags.json'
    if ($DryRun) {
      Emit-LogEvent -RunId ($runId + '-toggle-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would set warningsEnabled=false' -Inputs @($f) -Outputs @('would_set:warningsEnabled=false')
      Write-Output 'Dry run — would set warningsEnabled=false.'
      exit 0
    }
    $f = Ensure-RuntimeFlags
    $obj = Get-Content $f -Raw | ConvertFrom-Json
    $obj.warningsEnabled = $false
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $f -Encoding utf8
    Emit-LogEvent -RunId ($runId + '-toggle') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'SETTING_TOGGLED' -Summary 'warningsEnabled=false' -Inputs @($f) -Outputs @('warningsEnabled=false')
    Write-Output 'Done — warnings are now off.'
    exit 0
  }
  if ($toggleWarnOn | Where-Object { $m.Contains($_) }) {
    $f = 'config/runtime_flags.json'
    if ($DryRun) {
      Emit-LogEvent -RunId ($runId + '-toggle-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would set warningsEnabled=true' -Inputs @($f) -Outputs @('would_set:warningsEnabled=true')
      Write-Output 'Dry run — would set warningsEnabled=true.'
      exit 0
    }
    $f = Ensure-RuntimeFlags
    $obj = Get-Content $f -Raw | ConvertFrom-Json
    $obj.warningsEnabled = $true
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $f -Encoding utf8
    Emit-LogEvent -RunId ($runId + '-toggle') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'SETTING_TOGGLED' -Summary 'warningsEnabled=true' -Inputs @($f) -Outputs @('warningsEnabled=true')
    Write-Output 'Done — warnings are now on.'
    exit 0
  }
  if ($m.Contains('apply latest')) {
    $sid = Get-LatestReadyBuildId
    if ([string]::IsNullOrWhiteSpace($sid)) { Write-Output 'Done — there is no ready build to apply.'; exit 0 }
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would apply the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid | Out-Null
      Write-Output 'Done — applied the latest ready build.'
    }
    exit 0
  }
  if ($m.Contains('reject latest')) {
    $sid = Get-LatestReadyBuildId
    if ([string]::IsNullOrWhiteSpace($sid)) { Write-Output 'Done — there is no ready build to reject.'; exit 0 }
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would reject the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid | Out-Null
      Write-Output 'Done — rejected the latest ready build.'
    }
    exit 0
  }
  if ($m.Contains('show pending builds') -or $m.Contains('builds waiting for approval')) {
    $arr = python scripts/automation/build_session.py show --limit 10 | ConvertFrom-Json
    $ready = @($arr | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' })
    if ($ready.Count -eq 0) { Write-Output 'No builds waiting for approval.'; exit 0 }
    Write-Output ("Pending approvals: " + $ready.Count)
    Write-Output ('Latest: ' + [string]$ready[0].description)
    exit 0
  }
  if ($m.Contains('show latest status')) {
    $one = python scripts/automation/build_session.py show --limit 1 | ConvertFrom-Json
    if ($one.Count -eq 0) { Write-Output 'No build session yet.'; exit 0 }
    Write-Output ('Latest build status: ' + [string]$one[0].state)
    exit 0
  }
  if ($m.Contains('show logs summary')) {
    Write-Output 'Recent activity is available in the logger channel.'
    exit 0
  }
  if ($m.Contains('queue status')) {
    $qs = Get-QueueStatus
    $active = $qs.Active
    $queue = @($qs.Queue)
    if ($null -eq $active) {
      if ($queue.Count -eq 0) {
        Write-Output 'Queue is empty. No active build.'
      } else {
        Write-Output ("No active build. Queued: " + $queue.Count)
        $top = @($queue | Select-Object -First 3)
        foreach ($j in $top) { Write-Output ("- " + [string]$j.question) }
      }
    } else {
      Write-Output ("Active: " + [string]$active.question)
      Write-Output ("Queued: " + $queue.Count)
      $top = @($queue | Select-Object -First 3)
      foreach ($j in $top) { Write-Output ("- next: " + [string]$j.question) }
    }
    Emit-LogEvent -RunId ($runId + '-queue-status') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_STATUS' -Summary 'Queue status requested' -Inputs @($Message) -Outputs @(("active=" + [string]($null -ne $active)),("queued=" + $queue.Count))
    exit 0
  }
  if ($m.Contains('cancel next')) {
    $res = Cancel-NextJob
    if ($res.Cancelled) {
      Write-Output ("Cancelled next queued build: " + [string]$res.Job.question)
      Emit-LogEvent -RunId ($runId + '-cancel-next') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_CANCEL_NEXT' -Summary 'Cancelled next queued build' -Inputs @($Message) -Outputs @([string]$res.Job.job_id)
    } else {
      Write-Output 'No queued build to cancel.'
    }
    exit 0
  }
  if ($m.Contains('clear queue')) {
    $res = Clear-Queue
    Write-Output ("Cleared queued builds: " + $res.Cleared)
    Emit-LogEvent -RunId ($runId + '-clear-queue') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_CLEARED' -Summary ('Cleared queued builds: ' + $res.Cleared) -Inputs @($Message) -Outputs @([string]$res.Cleared)
    exit 0
  }
  if ($m.Contains('show debug') -or $m.Contains('details')) {
    python scripts/automation/build_session.py show --limit 5
    Get-Content task_ledger.jsonl -Tail 10
    exit 0
  }
  Write-Output 'Done — say what you want changed and I will route it automatically.'
  exit 0
}

# BUILD_PATH
if ($DryRun) {
  Emit-LogEvent -RunId ($runId + '-build-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would execute BUILD_PATH and start verification loop' -Inputs @($Message) -Outputs @('would_run:scripts/automation/run_work.ps1')
  Write-Output 'Dry run - would route to BUILD_PATH and start verification, then request approval.'
  exit 0
}
$enqueue = Enqueue-BuildJob -Question $Message -ChatId $ChatId -MessageId $MessageId -UpdateId $UpdateId -IdemKey $idemKey
if ($enqueue.QueueFull) {
  Emit-LogEvent -RunId ($runId + '-queue-full') -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'QUEUE_FULL' -Summary ('Build queue full (cap=' + $enqueue.Cap + ')') -Inputs @($Message) -Outputs @('queue_full')
  Write-Output 'Queue is full right now. Please try again after current builds finish.'
  exit 9
}
if ($enqueue.Duplicate) {
  Write-Output 'Already queued. I will process it after the current build finishes.'
  exit 0
}
$jobId = [string]$enqueue.Job.job_id
$pos = [int]$enqueue.Position
Emit-LogEvent -RunId ($runId + '-enqueued') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'BUILD_ENQUEUED' -Summary ('Build enqueued: ' + $jobId + ' position=' + $pos) -Inputs @($Message) -Outputs @($jobId,('position=' + $pos))
Write-Output ('Queued. Position: ' + $pos + '. I’ll start it after the current build finishes.')
