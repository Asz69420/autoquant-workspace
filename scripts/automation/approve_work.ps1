# LEGACY task-level approval; prefer scripts/automation/approve_build_session.ps1
param(
  [Parameter(Mandatory = $true)][ValidateSet('APPROVE','REJECT')][string]$Action,
  [Parameter(Mandatory = $true)][string]$TaskId
)

$ErrorActionPreference = 'Stop'

# Preconditions
python scripts/automation/evidence_gate.py --task-id $TaskId --claim READY_FOR_USER_APPROVAL | Out-Null

if ($Action -eq 'REJECT') {
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace "Rejected by user" | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Write-Output "REJECTED taskId=$TaskId"
  exit 0
}

$applySession = "approve_work:" + $PID
$finalArtifact = "artifacts/approved/${TaskId}-applied.txt"
New-Item -ItemType Directory -Force -Path "artifacts/approved" | Out-Null
$ts = [DateTimeOffset]::UtcNow.ToString("o")
Set-Content -Path $finalArtifact -Value ("task_id=$TaskId`napplied_at=$ts`nsource=run_work_smoke`n") -Encoding utf8

python scripts/automation/task_ledger.py update --task-id $TaskId --state APPLIED --pid-or-session $applySession --artifact $finalArtifact | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim APPLIED | Out-Null

Write-Output "APPLIED taskId=$TaskId apply_session=$applySession final_artifact=$finalArtifact"
