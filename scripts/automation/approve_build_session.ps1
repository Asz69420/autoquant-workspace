param(
  [Parameter(Mandatory = $true)][ValidateSet('APPROVE','REJECT')][string]$Action,
  [string]$BuildSessionId,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Emit-LogEvent {
  param(
    [string]$RunId,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary,
    [string[]]$Outputs
  )
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','build_session','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  python @args | Out-Null
}

if ([string]::IsNullOrWhiteSpace($BuildSessionId)) {
  $latest = python scripts/automation/build_session.py show --limit 1 | ConvertFrom-Json
  if ($latest.Count -eq 0) { throw 'No build session found' }
  $BuildSessionId = [string]$latest[0].build_session_id
}

$session = python scripts/automation/build_session.py show --build-session-id $BuildSessionId | ConvertFrom-Json
if ($session.state -ne 'SESSION_READY_FOR_APPROVAL') {
  throw "Session not ready for approval: $($session.state)"
}

if ($DryRun) {
  if ($Action -eq 'REJECT') {
    Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-dryrun") -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary ("Dry run - would reject build: " + $BuildSessionId) -Outputs @('would_set_state=BLOCKED')
    Write-Output "DRY_RUN build_session_id=$BuildSessionId action=REJECT would_set_state=BLOCKED"
    exit 0
  }
  Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-dryrun") -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary ("Dry run - would apply build: " + $BuildSessionId) -Outputs @('would_set_state=SESSION_APPLIED')
  Write-Output "DRY_RUN build_session_id=$BuildSessionId action=APPROVE would_set_state=SESSION_APPLIED"
  exit 0
}

if ($Action -eq 'REJECT') {
  python scripts/automation/build_session.py set-state --build-session-id $BuildSessionId --state BLOCKED --blocker-trace "Rejected by user" | Out-Null
  Emit-LogEvent -RunId ("build-" + $BuildSessionId) -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'BUILD_REJECTED' -Summary ("Build rejected: " + $BuildSessionId) -Outputs @('Rejected by user')
  Write-Output "BUILD_BLOCKED build_session_id=$BuildSessionId reason=Rejected by user"
  exit 0
}

$applyArtifact = "artifacts/approved/${BuildSessionId}-session-applied.txt"
New-Item -ItemType Directory -Force -Path "artifacts/approved" | Out-Null
$ts = [DateTimeOffset]::UtcNow.ToString("o")
Set-Content -Path $applyArtifact -Value ("build_session_id=$BuildSessionId`napplied_at=$ts`n") -Encoding utf8

$applyEvidence = "approve_build_session:" + $PID
python scripts/automation/build_session.py set-state --build-session-id $BuildSessionId --state SESSION_APPLIED --apply-evidence $applyEvidence | Out-Null
Emit-LogEvent -RunId ("build-" + $BuildSessionId) -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'BUILD_APPLIED' -Summary ("Build applied: " + $BuildSessionId) -Outputs @($applyEvidence, $applyArtifact)

Write-Output "SESSION_APPLIED build_session_id=$BuildSessionId apply_evidence=$applyEvidence artifact=$applyArtifact"
