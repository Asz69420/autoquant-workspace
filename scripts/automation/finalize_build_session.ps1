param(
  [string]$BuildSessionId
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BuildSessionId)) {
  $latest = python scripts/automation/build_session.py show --limit 1 | ConvertFrom-Json
  if ($latest.Count -eq 0) { throw 'No build session found' }
  $BuildSessionId = [string]$latest[0].build_session_id
}

$session = python scripts/automation/build_session.py show --build-session-id $BuildSessionId | ConvertFrom-Json
if ($session.state -ne 'ACTIVE') {
  throw "Session not ACTIVE: $($session.state)"
}

python scripts/automation/build_session.py set-state --build-session-id $BuildSessionId --state SESSION_READY_FOR_APPROVAL | Out-Null

Write-Output "SESSION_READY_FOR_APPROVAL build_session_id=$BuildSessionId"
Write-Output "Files changed: $(([string[]]$session.artifacts) -join ', ')"
Write-Output "Verifier runIds: $(([string[]]$session.verifier_run_ids) -join ', ')"
Write-Output "Ready to apply these changes. Want me to apply them?"
