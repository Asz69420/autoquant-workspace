param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId,
  [string]$BuildSessionId,
  [int]$MaxAttempts = 3,
  [switch]$SimulateFail
)

$ErrorActionPreference = 'Stop'

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
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','build_session','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Inputs) { foreach($i in $Inputs){ $args += @('--inputs',$i) } }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  python @args | Out-Null
}

if ([string]::IsNullOrWhiteSpace($BuildSessionId)) {
  $startOut = python scripts/automation/build_session.py start --description $Question
  $startObj = $startOut | ConvertFrom-Json
  $BuildSessionId = [string]$startObj.build_session_id
}

if ([string]::IsNullOrWhiteSpace($TaskId)) {
  $ts = Get-Date -Format "yyyyMMdd-HHmmss"
  $rand = ([guid]::NewGuid().ToString('N')).Substring(0,6)
  $TaskId = "$BuildSessionId-task-$ts-$rand"
}

$createOut = python scripts/automation/task_ledger.py create --task-id $TaskId --description $Question 2>&1
if ($LASTEXITCODE -ne 0) {
  if (-not ($createOut -match 'task_id already exists')) {
    throw ($createOut | Out-String)
  }
}

$pidSession = "run_work:" + $PID
python scripts/automation/task_ledger.py update --task-id $TaskId --state EXECUTING --pid-or-session $pidSession | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim EXECUTING | Out-Null

# Minimal harmless work artifact for controlled tasks
$artifact = "scripts/tests/run_work_smoke.txt"
$content = "task_id=$TaskId`nquestion=$Question`nts=" + ([DateTimeOffset]::UtcNow.ToString("o")) + "`n"
Set-Content -Path $artifact -Value $content -Encoding utf8

$finalRunId = ""
$finalVerdict = ""
$attempt = 0
$issues = @()

while ($attempt -lt $MaxAttempts) {
  $attempt += 1

  $verifyMessage = "Verify task ${TaskId}: file ${artifact} exists and includes task_id=${TaskId}. "
  if ($SimulateFail -and $attempt -eq 1) {
    $verifyMessage += "Also require AUTO_FIX_OK=1 to PASS. Return PASS/PARTIAL/FAIL concise with actionable issues."
  } else {
    $verifyMessage += "Return PASS/PARTIAL/FAIL concise with actionable issues."
  }

  $verifyOut = openclaw agent --agent verifier --message $verifyMessage --json
  $runId = ""
  $verdictText = ""
  try {
    $verifyObj = $verifyOut | ConvertFrom-Json
    if ($verifyObj.runId) { $runId = [string]$verifyObj.runId }
    if ($verifyObj.result.payloads[0].text) { $verdictText = [string]$verifyObj.result.payloads[0].text }
  } catch {
    $runId = ""
    $verdictText = ""
  }

  if ([string]::IsNullOrWhiteSpace($runId) -or [string]::IsNullOrWhiteSpace($verdictText)) {
    $trace = ($verifyOut | Out-String).Trim()
    if ($trace.Length -gt 400) { $trace = $trace.Substring(0,400) }
    python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --artifact ("verifier_attempt=" + $attempt + ";run_id=none;verdict=UNPARSEABLE") --blocker-trace "verifier_parse_fail: $trace" | Out-Null
    python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
    Write-Output "BLOCKED taskId=$TaskId"
    exit 2
  }

  $verdict = if ($verdictText -match '(?im)^PASS\b') { 'PASS' } else { 'FAIL' }
  python scripts/automation/task_ledger.py update --task-id $TaskId --state EXECUTING --pid-or-session $pidSession --artifact ("verifier_attempt=" + $attempt + ";run_id=" + $runId + ";verdict=" + $verdict) | Out-Null

  if ($verdict -eq 'PASS') {
    $finalRunId = $runId
    $finalVerdict = 'PASS'
    break
  }

  $issue = ($verdictText.Trim())
  if ($issue.Length -gt 240) { $issue = $issue.Substring(0,240) }
  $issues += $issue

  # minimal auto-fix step based on verifier fail
  Add-Content -Path $artifact -Value ("AUTO_FIX_OK=1;attempt=" + $attempt)
}

if ($finalVerdict -ne 'PASS') {
  $last = if ($issues.Count -gt 0) { $issues[-1] } else { 'Verifier failed with unresolved issues.' }
  $unresolved = ($issues | Select-Object -Unique) -join ' | '
  if ($unresolved.Length -gt 400) { $unresolved = $unresolved.Substring(0,400) }
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace ("max_attempts_reached: " + $last + " ; unresolved: " + $unresolved + " ; next: review artifact and rerun") | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId) -StatusWord 'FAIL' -StatusEmoji '❌' -ReasonCode 'VERIFIER_FAIL' -Summary ("Build blocked after max attempts: task=" + $TaskId) -Inputs @($TaskId) -Outputs @($unresolved)
  Write-Output "BLOCKED taskId=$TaskId reason=MAX_ATTEMPTS_REACHED"
  exit 3
}

python scripts/automation/task_ledger.py update --task-id $TaskId --state READY_FOR_USER_APPROVAL --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $finalRunId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim READY_FOR_USER_APPROVAL | Out-Null
python scripts/automation/build_session.py add-task --build-session-id $BuildSessionId --task-id $TaskId --artifact $artifact --verifier-run-id $finalRunId | Out-Null

# auto-finalize session (single-approval UX)
$finalizeOut = powershell -ExecutionPolicy Bypass -File scripts/automation/finalize_build_session.ps1 -BuildSessionId $BuildSessionId
Emit-LogEvent -RunId ("build-" + $BuildSessionId) -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'BUILD_READY_FOR_APPROVAL' -Summary ("Build ready for approval: " + $BuildSessionId + " attempts=" + $attempt) -Inputs @($TaskId) -Outputs @($artifact, ("verifier-run:" + $finalRunId))

Write-Output "BUILD_READY_FOR_APPROVAL build_session_id=$BuildSessionId"
Write-Output "Build ready. Verifier PASS (attempts=$attempt). Files changed: $artifact. Want me to apply these changes?"
