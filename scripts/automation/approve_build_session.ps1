param(
  [Parameter(Mandatory = $true)][ValidateSet('APPROVE','REJECT')][string]$Action,
  [string]$BuildSessionId
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BuildSessionId)) {
  $latest = python scripts/automation/build_session.py show --limit 1 | ConvertFrom-Json
  if ($latest.Count -eq 0) { throw 'No build session found' }
  $BuildSessionId = [string]$latest[0].build_session_id
}

$session = python scripts/automation/build_session.py show --build-session-id $BuildSessionId | ConvertFrom-Json
if ($session.state -ne 'SESSION_READY_FOR_APPROVAL') {
  throw "Session not ready for approval: $($session.state)"
}

if ($Action -eq 'REJECT') {
  python scripts/automation/build_session.py set-state --build-session-id $BuildSessionId --state BLOCKED --blocker-trace "Rejected by user" | Out-Null
  Write-Output "BUILD_BLOCKED build_session_id=$BuildSessionId reason=Rejected by user"
  exit 0
}

$applyArtifact = "artifacts/approved/${BuildSessionId}-session-applied.txt"
New-Item -ItemType Directory -Force -Path "artifacts/approved" | Out-Null
$ts = [DateTimeOffset]::UtcNow.ToString("o")
Set-Content -Path $applyArtifact -Value ("build_session_id=$BuildSessionId`napplied_at=$ts`n") -Encoding utf8

$applyEvidence = "approve_build_session:" + $PID
python scripts/automation/build_session.py set-state --build-session-id $BuildSessionId --state SESSION_APPLIED --apply-evidence $applyEvidence | Out-Null

Write-Output "SESSION_APPLIED build_session_id=$BuildSessionId apply_evidence=$applyEvidence artifact=$applyArtifact"
