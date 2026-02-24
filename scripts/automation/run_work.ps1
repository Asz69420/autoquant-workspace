param(
  [Parameter(Mandatory = $true)][string]$Question,
  [string]$TaskId,
  [string]$BuildSessionId,
  [int]$MaxAttempts = 3,
  [int]$MaxFixTimeSeconds = 120,
  [int]$MaxTotalEditsPerRun = 3,
  [string]$ExecutorType = 'LOCAL_SCRIPT',
  [switch]$AllowRescope,
  [switch]$SimulateFail,
  [switch]$SimulateMultiIssue,
  [switch]$SimulateRepeatIssue,
  [switch]$SimulateMinorOnly
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

if ([string]::IsNullOrWhiteSpace($ExecutorType)) {
  Write-Output 'FAIL reason_code=EXECUTOR_NOT_CONFIGURED'
  exit 12
}
if ($ExecutorType -notin @('LOCAL_SCRIPT','PROVIDER_MODEL')) {
  Write-Output 'FAIL reason_code=EXECUTOR_NOT_CONFIGURED'
  exit 12
}

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
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  python @args 2>$null | Out-Null
  $ErrorActionPreference = $oldEap
}

function Apply-AutofixText {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$newText
  )
  if ([string]::IsNullOrWhiteSpace($newText)) {
    python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace "autofix_missing_replacement_text" | Out-Null
    python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
    throw 'autofix_missing_replacement_text'
  }
  Add-Content -Path $Path -Value $newText
}

function Get-TextSha256Hex {
  param([string]$Text)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$Text)
    $hash = $sha.ComputeHash($bytes)
    return ([System.BitConverter]::ToString($hash)).Replace("-","").ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

function Get-FileSha256OrEmpty {
  param([string]$Path)
  if (Test-Path $Path) {
    try { return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant() } catch { return "" }
  }
  return ""
}

function New-ContextManifest {
  param(
    [string]$TaskId,
    [string]$BuildSessionId,
    [int]$TopN,
    [int]$MaxAttempts,
    [int]$MaxFixTimeSeconds,
    [int]$MaxTotalEditsPerRun
  )

  $changedFiles = @()
  $diffText = ""
  try {
    $null = (& git rev-parse --is-inside-work-tree 2>$null)
    if ($LASTEXITCODE -eq 0) {
      $nameOnly = (& git diff --name-only 2>$null)
      if ($LASTEXITCODE -eq 0 -and $nameOnly) {
        $changedFiles = @($nameOnly | ForEach-Object { $_.Trim() } | Where-Object { $_ })
      }
      $diffText = (& git diff 2>$null | Out-String)
      if ($LASTEXITCODE -ne 0) { $diffText = "" }
    }
  } catch {
    $diffText = ""
  }

  $contractHashes = [ordered]@{
    "USER.md" = (Get-FileSha256OrEmpty -Path "USER.md")
    "AGENTS-CORE.md" = (Get-FileSha256OrEmpty -Path "AGENTS-CORE.md")
    "SOUL-DIGEST.md" = (Get-FileSha256OrEmpty -Path "SOUL-DIGEST.md")
    "docs/CONTRACTS/verification-gate.md" = (Get-FileSha256OrEmpty -Path "docs/CONTRACTS/verification-gate.md")
  }

  $diffSha = if ([string]::IsNullOrEmpty($diffText)) { "" } else { Get-TextSha256Hex -Text $diffText }
  $scopeSource = ([ordered]@{
    diff_sha256 = $diffSha
    changed_files = $changedFiles
    contract_hashes = $contractHashes
  } | ConvertTo-Json -Depth 6 -Compress)
  $scopeFingerprint = Get-TextSha256Hex -Text $scopeSource

  $manifest = [ordered]@{
    task_id = $TaskId
    build_session_id = $BuildSessionId
    ts_iso = ([DateTimeOffset]::UtcNow.ToString("o"))
    changed_files = $changedFiles
    diff_sha256 = $diffSha
    contract_hashes = $contractHashes
    topn = $TopN
    max_attempts = $MaxAttempts
    max_fix_time_seconds = $MaxFixTimeSeconds
    max_total_edits_per_run = $MaxTotalEditsPerRun
    scope_fingerprint = $scopeFingerprint
  }

  $manifestDir = "artifacts/verification/$TaskId"
  New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
  $manifestPath = "$manifestDir/context_manifest.json"
  ($manifest | ConvertTo-Json -Depth 8) | Set-Content -Path $manifestPath -Encoding utf8

  return [pscustomobject]@{
    path = $manifestPath
    diff_sha256 = $diffSha
    contract_hashes_json = ($contractHashes | ConvertTo-Json -Compress)
  }
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

# single-flight guard: only one EXECUTING task per build session
if (Test-Path 'task_ledger.jsonl') {
  $activeTaskId = python -c "import json,pathlib; sid='$BuildSessionId'; latest={};
for l in pathlib.Path('task_ledger.jsonl').read_text(encoding='utf-8').splitlines():
  if not l.strip(): continue
  o=json.loads(l)
  tid=o.get('task_id','')
  if tid.startswith(sid+'-task-'): latest[tid]=o
act=[v.get('task_id') for v in latest.values() if v.get('state')=='EXECUTING']
print(act[0] if act else '')"
  if (-not [string]::IsNullOrWhiteSpace($activeTaskId)) {
    python scripts/automation/task_ledger.py create --task-id $TaskId --description $Question | Out-Null
    python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace ("single_flight_active: " + $activeTaskId + " ; wait until READY_FOR_USER_APPROVAL/SESSION_APPLIED/BLOCKED") | Out-Null
    python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
    Write-Output "Blocked - another build task is already running for this build session."
    exit 7
  }
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

$contextManifest = New-ContextManifest -TaskId $TaskId -BuildSessionId $BuildSessionId -TopN 10 -MaxAttempts $MaxAttempts -MaxFixTimeSeconds $MaxFixTimeSeconds -MaxTotalEditsPerRun $MaxTotalEditsPerRun
$baselineDiffSha = [string]$contextManifest.diff_sha256
$baselineContractHashesJson = [string]$contextManifest.contract_hashes_json

$finalRunId = ""
$finalVerdict = ""
$attempt = 0
$issues = @()
$startAt = Get-Date
$warnOnly = $false
$lastVerifierOutPath = ""
$totalEdits = 0
$issueSigCounts = @{}

while ($attempt -lt $MaxAttempts) {
  if (((Get-Date) - $startAt).TotalSeconds -gt $MaxFixTimeSeconds) { break }
  $attempt += 1

  $contextManifest = New-ContextManifest -TaskId $TaskId -BuildSessionId $BuildSessionId -TopN 10 -MaxAttempts $MaxAttempts -MaxFixTimeSeconds $MaxFixTimeSeconds -MaxTotalEditsPerRun $MaxTotalEditsPerRun
  $driftDetected = (($contextManifest.diff_sha256 -ne $baselineDiffSha) -or ($contextManifest.contract_hashes_json -ne $baselineContractHashesJson))
  if ($driftDetected -and -not $AllowRescope) {
    $trace = "CONTEXT_DRIFT: manifest changed mid-loop; explicit re-scope approval required"
    python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --artifact ("context_manifest=" + $contextManifest.path) --blocker-trace $trace | Out-Null
    python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
    Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId) -StatusWord 'WARN' -StatusEmoji 'WARN' -ReasonCode 'CONTEXT_DRIFT' -Summary ("Build blocked due to context drift: task=" + $TaskId) -Inputs @($TaskId) -Outputs @($contextManifest.path)
    Write-Output "Blocked - context drift detected. Explicit re-scope approval is required."
    exit 9
  }

  $verifyMessage = "Verify task ${TaskId}: file ${artifact} exists and includes task_id=${TaskId}. Read and use this manifest: $($contextManifest.path). Base checks on changed_files + contract_hashes from the manifest (freshness pinned). Return JSON when possible: {verdict,total_issues_found,issues_returned,issues:[{severity,file,message,suggested_fix}],manifest_path_used}. If JSON not possible, return text with 'total issues: X' and up to TopN=10 actionable issues. Prioritize CRITICAL then MAJOR then MINOR within TopN. "
  if (($SimulateFail -and $attempt -eq 1) -or ($isSmoke -and $attempt -eq 1)) {
    $verifyMessage += "For smoke validation require AUTO_FIX_OK=1 to PASS. "
  }
  if ($SimulateMultiIssue -and $attempt -eq 1) {
    $verifyMessage += "For synthetic multi-issue validation require BATCH_FIX_OK=1 and AUTO_FIX_OK=1 to PASS. "
  }
  if ($SimulateRepeatIssue) {
    $verifyMessage += "Emit the same MAJOR issue signature each run: file=scripts/tests/run_work_smoke.txt message='REPEAT_SIG_DEMO'. "
  }
  if ($SimulateMinorOnly) {
    if ($attempt -ge 2) {
      $verifyMessage += "Return WARN with only MINOR issue(s), include total_issues_found and issues_returned, no CRITICAL/MAJOR. "
    } else {
      $verifyMessage += "Emit only MINOR issues if any remain; no CRITICAL/MAJOR. "
    }
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
    Write-Output "Blocked - verifier output could not be parsed. Say 'show debug' for details."
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

  # issue signature tracking + early stop
  $sigList = @()
  foreach ($it in $issuesReturned) {
    $sig = (($it -replace '\s+',' ').Trim())
    if (-not [string]::IsNullOrWhiteSpace($sig)) {
      $sigList += $sig
      if (-not $issueSigCounts.ContainsKey($sig)) { $issueSigCounts[$sig] = 0 }
      $issueSigCounts[$sig] = [int]$issueSigCounts[$sig] + 1
    }
  }
  $repeatSig = $null
  foreach ($k in $issueSigCounts.Keys) { if ($issueSigCounts[$k] -ge 2) { $repeatSig = $k; break } }
  if ($repeatSig -and $verdict -ne 'PASS') {
    $trace = "REPEATED_ISSUE_SIGNATURE: $repeatSig ; next: manual intervention required"
    python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace $trace | Out-Null
    python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
    Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId) -StatusWord 'FAIL' -StatusEmoji 'FAIL' -ReasonCode 'VERIFIER_FAIL' -Summary ("Build blocked early-stop repeated issue: task=" + $TaskId) -Inputs @($TaskId) -Outputs @($lastVerifierOutPath)
    Write-Output "Blocked - the same verification issue repeated. Say 'show debug' for details."
    exit 8
  }

  # Batch-fix all returned issues in one pass (token-driven minimal fixes)
  $filesTouched = @()
  if ($verdict -ne 'PASS') {
    if ($isSmoke -and $verdictText -match 'AUTO_FIX_OK=1') {
      Apply-AutofixText -Path "scripts/tests/run_work_smoke.txt" -newText "AUTO_FIX_OK=1"
      $filesTouched += "scripts/tests/run_work_smoke.txt"
    }
    if ($verdictText -match 'BATCH_FIX_OK=1') {
      Apply-AutofixText -Path $artifact -newText "BATCH_FIX_OK=1"
      $filesTouched += $artifact
    }
  }

  $filesTouched = @($filesTouched | Select-Object -Unique | Select-Object -First $MaxTotalEditsPerRun)
  $issuesAddressedCount = $filesTouched.Count
  $totalEdits += $issuesAddressedCount

  python scripts/automation/task_ledger.py update --task-id $TaskId --state EXECUTING --pid-or-session $pidSession --artifact ("verifier_attempt=" + $attempt + ";run_id=" + $runId + ";verdict=" + $verdict + ";total_issues_found=" + $totalIssues + ";issues_returned=" + $issuesReturned.Count + ";issues_addressed_count=" + $issuesAddressedCount + ";files_touched=" + (($filesTouched -join ',') -replace ' ','_')) --artifact ("verifier_output_artifact=" + $verifierOutPath) --artifact ("context_manifest=" + $contextManifest.path) | Out-Null
  Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId + "-attempt-" + $attempt) -StatusWord 'INFO' -StatusEmoji 'INFO' -ReasonCode 'VERIFIER_ATTEMPT' -Summary ("Verifier attempt=" + $attempt + " verdict=" + $verdict + " issues_returned=" + $issuesReturned.Count) -Inputs @($TaskId) -Outputs @($verifierOutPath)

  if ($verdict -eq 'PASS') {
    $finalRunId = $runId
    $finalVerdict = 'PASS'
    break
  }

  $hasMajor = ($severityList -contains 'CRITICAL' -or $severityList -contains 'MAJOR')
  if ($attempt -ge 2 -and -not $hasMajor -and $issuesReturned.Count -gt 0) {
    $warnOnly = $true
    $finalRunId = $runId
    $finalVerdict = 'WARN'
    break
  }

  if ($totalEdits -ge $MaxTotalEditsPerRun) {
    break
  }

  $issue = ($verdictText.Trim())
  if ($issue.Length -gt 240) { $issue = $issue.Substring(0,240) }
  $issues += $issue

  # minor-only handling is evaluated earlier (attempt>=2) to limit churn
}

if ($finalVerdict -eq '') {
  $last = if ($issues.Count -gt 0) { $issues[-1] } else { 'Verifier failed with unresolved issues.' }
  $unresolved = ($issues | Select-Object -Unique) -join ' | '
  if ($unresolved.Length -gt 400) { $unresolved = $unresolved.Substring(0,400) }
  $lastSafe = ($last -replace '[^a-zA-Z0-9 _\-\.:]','')
  $unresolvedSafe = ($unresolved -replace '[^a-zA-Z0-9 _\-\.:|]','')
  $elapsed = [int]((Get-Date) - $startAt).TotalSeconds
  $reason = if ($elapsed -gt $MaxFixTimeSeconds) { 'MAX_FIX_TIME_EXCEEDED' } elseif ($totalEdits -ge $MaxTotalEditsPerRun) { 'MAX_TOTAL_EDITS_REACHED' } else { 'MAX_ATTEMPTS_REACHED' }
  $traceMsg = ($reason + ": " + $lastSafe + " ; unresolved: " + $unresolvedSafe + " ; next: review artifact and rerun")
  python scripts/automation/task_ledger.py update --task-id $TaskId --state BLOCKED --blocker-trace $traceMsg | Out-Null
  python scripts/automation/evidence_gate.py --task-id $TaskId --claim BLOCKED | Out-Null
  Emit-LogEvent -RunId ("build-" + $BuildSessionId + "-" + $TaskId) -StatusWord 'FAIL' -StatusEmoji 'FAIL' -ReasonCode 'VERIFIER_FAIL' -Summary ("Build blocked: task=" + $TaskId + " reason=" + $reason) -Inputs @($TaskId) -Outputs @($unresolved, $lastVerifierOutPath)
  Write-Output "Blocked - couldn't pass verification within limits. Say 'show debug' for details."
  exit 3
}

python scripts/automation/task_ledger.py update --task-id $TaskId --state READY_FOR_USER_APPROVAL --artifact $artifact --verifier-or-audit-artifact ("verifier-run:" + $finalRunId) | Out-Null
python scripts/automation/evidence_gate.py --task-id $TaskId --claim READY_FOR_USER_APPROVAL | Out-Null
python scripts/automation/build_session.py add-task --build-session-id $BuildSessionId --task-id $TaskId --artifact $artifact --verifier-run-id $finalRunId | Out-Null

# auto-finalize session (single-approval UX)
$sessionState = ''
try {
  $sessionObj = python scripts/automation/build_session.py show --build-session-id $BuildSessionId | ConvertFrom-Json
  $sessionState = [string]$sessionObj.state
} catch { $sessionState = '' }
if ($sessionState -eq 'ACTIVE') {
  $finalizeOut = powershell -ExecutionPolicy Bypass -File scripts/automation/finalize_build_session.ps1 -BuildSessionId $BuildSessionId
}
$readySummary = if ($finalVerdict -eq 'WARN') { "Build ready with WARN-only minor issues: " + $BuildSessionId + " attempts=" + $attempt } else { "Build ready for approval: " + $BuildSessionId + " attempts=" + $attempt }
Emit-LogEvent -RunId ("build-" + $BuildSessionId) -StatusWord 'INFO' -StatusEmoji 'INFO' -ReasonCode 'BUILD_READY_FOR_APPROVAL' -Summary $readySummary -Inputs @($TaskId) -Outputs @($artifact, ("verifier-run:" + $finalRunId))

# supersede older ready builds (hide stale approvals from main chat)
try {
  $sessions = python scripts/automation/build_session.py show --limit 50 | ConvertFrom-Json
  foreach ($s in $sessions) {
    if ($s.build_session_id -ne $BuildSessionId -and $s.state -eq 'SESSION_READY_FOR_APPROVAL') {
      python scripts/automation/build_session.py set-state --build-session-id $s.build_session_id --state SUPERSEDED --blocker-trace ("Superseded by " + $BuildSessionId) | Out-Null
      Emit-LogEvent -RunId ("build-" + [string]$s.build_session_id) -StatusWord 'INFO' -StatusEmoji 'INFO' -ReasonCode 'BUILD_SUPERSEDED' -Summary ("Build superseded by newer ready build") -Inputs @([string]$s.build_session_id) -Outputs @([string]$BuildSessionId)
    }
  }
} catch {}

Write-Output "Build ready for your review"
if ($finalVerdict -eq 'WARN') {
  Write-Output "- What changed: verifier loop and fixes completed"
  Write-Output "- Risk summary: WARN only (minor issues)"
  Write-Output "- User impact: no immediate live impact"
  Write-Output "Apply these changes?"
} else {
  Write-Output "- What changed: requested updates implemented and verified"
  Write-Output "- Risk summary: PASS"
  Write-Output "- User impact: no immediate live impact"
  Write-Output "Apply these changes?"
}
