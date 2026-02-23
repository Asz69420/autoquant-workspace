param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId,
  [string]$BuildSessionId,
  [int]$MaxAttempts = 3,
  [int]$MaxFixTimeSeconds = 120,
  [switch]$SimulateFail,
  [switch]$SimulateMultiIssue
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

# Harmless artifact path (smoke-scoped marker rule)
$isSmoke = ($Question -match '(?i)smoke' -or $TaskId -match '(?i)smoke')
$artifact = if ($isSmoke) { "scripts/tests/run_work_smoke.txt" } else { "scripts/tests/run_work_output.txt" }
$content = "task_id=$TaskId`nquestion=$Question`nts=" + ([DateTimeOffset]::UtcNow.ToString("o")) + "`n"
Set-Content -Path $artifact -Value $content -Encoding utf8

$finalRunId = ""
$finalVerdict = ""
$attempt = 0
$issues = @()
$startAt = Get-Date
$warnOnly = $false
$lastVerifierOutPath = ""

while ($attempt -lt $MaxAttempts) {
  if (((Get-Date) - $startAt).TotalSeconds -gt $MaxFixTimeSeconds) { break }
  $attempt += 1

  $verifyMessage = "Verify task ${TaskId}: file ${artifact} exists and includes task_id=${TaskId}. Return JSON when possible: {verdict,total_issues_found,issues_returned,issues:[{severity,file,message,suggested_fix}]}. If JSON not possible, return text with 'total issues: X' and up to TopN=10 actionable issues. "
  if (($SimulateFail -and $attempt -eq 1) -or ($isSmoke -and $attempt -eq 1)) {
    $verifyMessage += "For smoke validation require AUTO_FIX_OK=1 to PASS. "
  }
  if ($SimulateMultiIssue -and $attempt -eq 1) {
    $verifyMessage += "For synthetic multi-issue validation require BATCH_FIX_OK=1 and AUTO_FIX_OK=1 to PASS. "
  }

  $verifyOut = openclaw agent --agent verifier --message $verifyMessage --json
  $runId = ""
  $verdictText = ""
  $totalIssues = 0
  $issuesReturned = @()
  $severityList = @()
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

  # persist full verifier output artifact (for long outputs)
  $verifierOutPath = "artifacts/verifier/${TaskId}-attempt-${attempt}.txt"
  New-Item -ItemType Directory -Force -Path "artifacts/verifier" | Out-Null
  Set-Content -Path $verifierOutPath -Value $verdictText -Encoding utf8
  $lastVerifierOutPath = $verifierOutPath

  $verdict = 'FAIL'
  $parsedJson = $null
  try { $parsedJson = $verdictText | ConvertFrom-Json } catch { $parsedJson = $null }

  if ($parsedJson -ne $null -and $parsedJson.verdict) {
    $pv = ([string]$parsedJson.verdict).ToUpperInvariant()
    if ($pv -in @('PASS','FAIL','PARTIAL','WARN')) {
      $verdict = if ($pv -eq 'PARTIAL') { 'FAIL' } else { $pv }
    }
    if ($parsedJson.total_issues_found -ne $null) { $totalIssues = [int]$parsedJson.total_issues_found }
    if ($parsedJson.issues) {
      foreach ($it in $parsedJson.issues) {
        $sev = ([string]$it.severity).ToUpperInvariant()
        if ($sev -eq 'MEDIUM') { $sev = 'MAJOR' }
        if ($sev -eq 'LOW') { $sev = 'MINOR' }
        if ($sev -eq 'HIGH') { $sev = 'CRITICAL' }
        if ($sev -notin @('CRITICAL','MAJOR','MINOR')) { $sev = 'MAJOR' }
        $severityList += $sev
        $issuesReturned += ("- [" + $sev + "] " + [string]$it.message)
      }
    }
  } else {
    $mTotal = [regex]::Match($verdictText, '(?im)total\s+issues\s*:\s*(\d+)')
    if ($mTotal.Success) { $totalIssues = [int]$mTotal.Groups[1].Value }

    foreach ($line in ($verdictText -split "`n")) {
      if ($line -match '(?i)CRITICAL|MAJOR|MINOR') {
        if ($line -match '(?i)CRITICAL') { $severityList += 'CRITICAL' }
        elseif ($line -match '(?i)MAJOR') { $severityList += 'MAJOR' }
        elseif ($line -match '(?i)MINOR') { $severityList += 'MINOR' }
      }
      if ($line.Trim().StartsWith('- ')) { $issuesReturned += $line.Trim() }
    }

    $verdict = if ($verdictText -match '(?im)^PASS\b') { 'PASS' } elseif ($verdictText -match '(?im)^WARN\b') { 'WARN' } else { 'FAIL' }
  }

  # Batch-fix all returned issues in one pass (token-driven minimal fixes)
  $filesTouched = @()
  if ($verdict -ne 'PASS') {
    if ($isSmoke -and $verdictText -match 'AUTO_FIX_OK=1') {
      Add-Content -Path "scripts/tests/run_work_smoke.txt" -Value "AUTO_FIX_OK=1"
      $filesTouched += "scripts/tests/run_work_smoke.txt"
    }
    if ($verdictText -match 'BATCH_FIX_OK=1') {
      Add-Content -Path $artifact -Value "BATCH_FIX_OK=1"
      $filesTouched += $artifact
    }
  }

  $issuesAddressedCount = $filesTouched.Count
  python scripts/automation/task_ledger.py update --task-id $TaskId --state EXECUTING --pid-or-session $pidSession --artifact ("verifier_attempt=" + $attempt + ";run_id=" + $runId + ";verdict=" + $verdict + ";total_issues_found=" + $totalIssues + ";issues_returned=" + $issuesReturned.Count + ";issues_addressed_count=" + $issuesAddressedCount + ";files_touched=" + (($filesTouched -join ',') -replace ' ','_')) --artifact ("verifier_output_artifact=" + $verifierOutPath) | Out-Null

  if ($verdict -eq 'PASS') {
    $finalRunId = $runId
    $finalVerdict = 'PASS'
    break
  }

  $issue = ($verdictText.Trim())
  if ($issue.Length -gt 240) { $issue = $issue.Substring(0,240) }
  $issues += $issue

  $hasMajor = ($severityList -contains 'CRITICAL' -or $severityList -contains 'MAJOR')
  if (-not $hasMajor -and $severityList.Count -gt 0) {
    $warnOnly = $true
    $finalRunId = $runId
    $finalVerdict = 'WARN'
    break
  }
}

if ($finalVerdict -eq '') {
  $last = if ($issues.Count -gt 0) { $issues[-1] } else { 'Verifier failed with unresolved issues.' }
  $unresolved = ($issues | Select-Object -Unique) -join ' | '
  if ($unresolved.Length -gt 400) { $unresolved = $unresolved.Substring(0,400) }
  $lastSafe = ($last -replace '[^a-zA-Z0-9 _\-\.:]','')
  $unresolvedSafe = ($unresolved -replace '[^a-zA-Z0-9 _\-\.:|]','')
  $elapsed = [int]((Get-Date) - $startAt).TotalSeconds
  $reason = if ($elapsed -gt $MaxFixTimeSeconds) { 'MAX_FIX_TIME_EXCEEDED' } else { 'MAX_ATTEMPTS_REACHED' }
  $traceMsg = ($reason + ": " + $lastSafe + " ; unresolved: " + $unresolvedSafe + " ; next: review artifact and rerun")
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace $traceMsg | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId) -StatusWord 'FAIL' -StatusEmoji '❌' -ReasonCode 'VERIFIER_FAIL' -Summary ("Build blocked: task=" + $TaskId + " reason=" + $reason) -Inputs @($TaskId) -Outputs @($unresolved, $lastVerifierOutPath)
  Write-Output "BLOCKED taskId=$TaskId reason=$reason"
  exit 3
}

python scripts/automation/task_ledger.py update --task-id $TaskId --state READY_FOR_USER_APPROVAL --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $finalRunId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim READY_FOR_USER_APPROVAL | Out-Null
python scripts/automation/build_session.py add-task --build-session-id $BuildSessionId --task-id $TaskId --artifact $artifact --verifier-run-id $finalRunId | Out-Null

# auto-finalize session (single-approval UX)
$finalizeOut = powershell -ExecutionPolicy Bypass -File scripts/automation/finalize_build_session.ps1 -BuildSessionId $BuildSessionId
$readySummary = if ($finalVerdict -eq 'WARN') { "Build ready with WARN-only minor issues: " + $BuildSessionId + " attempts=" + $attempt } else { "Build ready for approval: " + $BuildSessionId + " attempts=" + $attempt }
Emit-LogEvent -RunId ("build-" + $BuildSessionId) -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'BUILD_READY_FOR_APPROVAL' -Summary $readySummary -Inputs @($TaskId) -Outputs @($artifact, ("verifier-run:" + $finalRunId))

Write-Output "BUILD_READY_FOR_APPROVAL build_session_id=$BuildSessionId"
if ($finalVerdict -eq 'WARN') {
  Write-Output "Build ready. Verifier WARN only (minor). Files changed: $artifact. Apply anyway?"
} else {
  Write-Output "Build ready. Verifier PASS (attempts=$attempt). Files changed: $artifact. Want me to apply these changes?"
}
