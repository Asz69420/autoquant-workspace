param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId,
  [string]$BuildSessionId
)

$ErrorActionPreference = 'Stop'

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

$verifyMessage = "Verify task ${TaskId}: file ${artifact} exists and includes task_id=${TaskId}. Return PASS/PARTIAL/FAIL concise."
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
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace "verifier_parse_fail: $trace" | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Write-Output "BLOCKED taskId=$TaskId"
  exit 2
}

if (-not ($verdictText -match '(?im)^PASS\b')) {
  $trace = ($verdictText.Trim())
  if ($trace.Length -gt 400) { $trace = $trace.Substring(0,400) }
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace "verifier_fail: $trace" | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Write-Output "BLOCKED taskId=$TaskId"
  exit 3
}

python scripts/automation/task_ledger.py update --task-id $TaskId --state COMPLETE --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $runId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim COMPLETE | Out-Null
python scripts/automation/build_session.py add-task --build-session-id $BuildSessionId --task-id $TaskId --artifact $artifact --verifier-run-id $runId | Out-Null

Write-Output "BUILD_SESSION_ACTIVE build_session_id=$BuildSessionId taskId=$TaskId artifact=$artifact verifier_run_id=$runId verdict=PASS"
Write-Output "No per-task approval required. Continue adding tasks, then finalize session for one approval."
Write-Output "powershell -ExecutionPolicy Bypass -File scripts/automation/finalize_build_session.ps1 -BuildSessionId $BuildSessionId"
