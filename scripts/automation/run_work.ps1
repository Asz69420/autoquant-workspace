param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($TaskId)) {
  $ts = Get-Date -Format "yyyyMMdd-HHmmss"
  $rand = ([guid]::NewGuid().ToString('N')).Substring(0,6)
  $TaskId = "task-$ts-$rand"
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

python scripts/automation/task_ledger.py update --task-id $TaskId --state READY_FOR_USER_APPROVAL --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $runId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim READY_FOR_USER_APPROVAL | Out-Null

Write-Output "READY_FOR_USER_APPROVAL taskId=$TaskId artifact=$artifact verifier_run_id=$runId verdict=PASS"
Write-Output "Generated taskId: $TaskId"
Write-Output "APPROVE taskId=$TaskId"
Write-Output "REJECT taskId=$TaskId"
Write-Output "powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action APPROVE -TaskId $TaskId"
Write-Output "powershell -ExecutionPolicy Bypass -File scripts/automation/approve_work.ps1 -Action REJECT -TaskId $TaskId"
