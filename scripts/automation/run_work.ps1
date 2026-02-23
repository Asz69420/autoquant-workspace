param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($TaskId)) {
  $TaskId = "task-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
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
try {
  $verifyObj = $verifyOut | ConvertFrom-Json
  if ($verifyObj.runId) { $runId = [string]$verifyObj.runId }
} catch {
  $runId = ""
}

if ([string]::IsNullOrWhiteSpace($runId)) {
  $trace = ($verifyOut | Out-String).Trim()
  if ($trace.Length -gt 400) { $trace = $trace.Substring(0,400) }
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace "verifier_parse_fail: $trace" | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Write-Output "BLOCKED taskId=$TaskId"
  exit 2
}

python scripts/automation/task_ledger.py update --task-id $TaskId --state COMPLETE --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $runId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim COMPLETE | Out-Null

Write-Output "COMPLETE taskId=$TaskId artifact=$artifact verifier_run_id=$runId"
