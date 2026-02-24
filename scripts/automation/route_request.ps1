param(
  [Parameter(Mandatory = $true)][string]$Message
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

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
$fastStatus = @('show pending builds','show latest status','show logs summary','show debug','details','help','usage')
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

$runId = 'route-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Emit-LogEvent -RunId $runId -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'ROUTE_DECISION' -Summary ("route=" + $route + "; rule=" + $rule) -Inputs @($Message) -Outputs @($route)

if ($route -eq 'FAST_PATH') {
  if ($toggleWarnOff | Where-Object { $m.Contains($_) }) {
    $f = Ensure-RuntimeFlags
    $obj = Get-Content $f -Raw | ConvertFrom-Json
    $obj.warningsEnabled = $false
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $f -Encoding utf8
    Emit-LogEvent -RunId ($runId + '-toggle') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'SETTING_TOGGLED' -Summary 'warningsEnabled=false' -Inputs @($f) -Outputs @('warningsEnabled=false')
    Write-Output 'Done — warnings are now off.'
    exit 0
  }
  if ($toggleWarnOn | Where-Object { $m.Contains($_) }) {
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
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid | Out-Null
    Write-Output 'Done — applied the latest ready build.'
    exit 0
  }
  if ($m.Contains('reject latest')) {
    $sid = Get-LatestReadyBuildId
    if ([string]::IsNullOrWhiteSpace($sid)) { Write-Output 'Done — there is no ready build to reject.'; exit 0 }
    powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid | Out-Null
    Write-Output 'Done — rejected the latest ready build.'
    exit 0
  }
  if ($m.Contains('show pending builds')) {
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
  if ($m.Contains('show debug') -or $m.Contains('details')) {
    python scripts/automation/build_session.py show --limit 5
    Get-Content task_ledger.jsonl -Tail 10
    exit 0
  }
  Write-Output 'Done — say what you want changed and I will route it automatically.'
  exit 0
}

# BUILD_PATH
Write-Output "Working on it - I'll verify it and then ask for approval."
$runOut = @()
$runCode = 0
try {
  $runOut = powershell -ExecutionPolicy Bypass -File scripts/automation/run_work.ps1 -Question $Message *>&1
  $runCode = $LASTEXITCODE
} catch {
  $runOut = @([string]$_.Exception.Message)
  $runCode = 1
}
if ($runCode -ne 0) {
  if ($debugOverride) {
    Write-MainChatFiltered -Lines @($runOut) -Debug $true
  } else {
    Write-Output "Blocked - couldn't pass verification within limits. Say 'show debug' for details."
  }
  exit $runCode
}
Write-MainChatFiltered -Lines @($runOut) -Debug $debugOverride
