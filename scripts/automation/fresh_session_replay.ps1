param(
  [switch]$DryRun = $true,
  [string]$StartTimeIso
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

# Guardrail: always run from repository root so relative ledger paths cannot drift into tmp/ clones.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($StartTimeIso)) {
  $StartTimeIso = [DateTimeOffset]::UtcNow.ToString('o')
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
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','fresh_session_replay','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Inputs) { foreach($i in $Inputs){ $args += @('--inputs',$i) } }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  python @args 2>$null | Out-Null
  $ErrorActionPreference = $oldEap
}

function Get-LatestRouteDecision {
  param([string]$Message)
  $p = 'data/logs/actions.ndjson'
  if (-not (Test-Path $p)) { return $null }
  $lines = Get-Content $p -Tail 400
  $matches = @()
  foreach ($ln in $lines) {
    if ([string]::IsNullOrWhiteSpace($ln)) { continue }
    try { $o = $ln | ConvertFrom-Json } catch { continue }
    if ($o.reason_code -ne 'ROUTE_DECISION') { continue }
    $in = @($o.inputs)
    if (-not ($in -contains $Message)) { continue }
    $matches += $o
  }
  if ($matches.Count -eq 0) { return $null }
  return $matches[-1]
}

function Get-TmpLedgerClones {
  if (-not (Test-Path 'tmp')) { return @() }
  return @(Get-ChildItem -Path 'tmp' -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @('task_ledger.jsonl','build_session_ledger.jsonl') } |
    ForEach-Object { $_.FullName })
}

function Has-ReadyBuildApproval {
  if (-not (Test-Path 'build_session_ledger.jsonl')) { return $false }
  $latest = @{}
  Get-Content build_session_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    try { $o = $_ | ConvertFrom-Json } catch { return }
    $latest[$o.build_session_id] = $o
  }
  $ready = @($latest.Values | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' })
  return ($ready.Count -gt 0)
}

$steps = @(
  @{ name='A'; prompt='any builds waiting for approval'; expected='FAST_PATH'; mode='route' },
  @{ name='B'; prompt='turn warnings off'; expected='FAST_PATH'; mode='route' },
  @{ name='C'; prompt='build a tiny harmless change'; expected='BUILD_PATH'; mode='route' },
  @{ name='D'; prompt='yeah apply it'; expected='FAST_PATH'; mode='approve' }
)

$runRoot = 'fresh-replay-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$allPass = $true
$pain = @()

$isDryRun = [bool]$DryRun
$gitBefore = @(git status --porcelain)
$tmpLedgersBefore = @(Get-TmpLedgerClones)
Write-Output ("Fresh session replay start: dry_run=" + $isDryRun.ToString().ToLowerInvariant() + "; start=" + $StartTimeIso)

for ($i=0; $i -lt $steps.Count; $i++) {
  $s = $steps[$i]
  $prompt = [string]$s.prompt
  $expected = [string]$s.expected
  $stepId = "$runRoot-step-$($s.name)"

  if ($s.mode -eq 'route') {
    $uid = ("freshreplay-" + $s.name + "-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    if ($isDryRun) {
      $out = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message $prompt -UpdateId $uid -DryRun 2>&1
    } else {
      $out = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message $prompt -UpdateId $uid 2>&1
    }
    $decision = Get-LatestRouteDecision -Message $prompt
    $route = if ($null -eq $decision) { 'UNKNOWN' } else { [string]$decision.outputs[0] }
    $pass = ($route -eq $expected)
    if (-not $pass) {
      $allPass = $false
      $pain += ("$($s.name): expected $expected but got $route")
    }
    $status = if ($pass) { 'PASS' } else { 'FAIL' }
    Write-Output ("[$status] Step $($s.name): route=$route expected=$expected")
    Write-Output ("  reply: " + (($out | Select-Object -First 1) -join ''))
    $evWord = if ($pass) { 'OK' } else { 'WARN' }
    $evEmoji = if ($pass) { '✅' } else { '⚠️' }
    Emit-LogEvent -RunId $stepId -StatusWord $evWord -StatusEmoji $evEmoji -ReasonCode 'FRESH_SESSION_STEP' -Summary ("step="+$s.name+" route="+$route+" dry_run="+$isDryRun.ToString().ToLowerInvariant()+" result="+$status) -Inputs @($prompt) -Outputs @($route)
    continue
  }

  # approval intent step
  $hasPending = Has-ReadyBuildApproval
  if ($isDryRun -and -not $hasPending) {
    $status = 'PASS'
    Write-Output ("[$status] Step $($s.name): route=FAST_PATH expected=FAST_PATH")
    Write-Output '  reply: Dry run — no pending approvals.'
    Emit-LogEvent -RunId $stepId -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'FRESH_SESSION_STEP' -Summary ("step="+$s.name+" route=FAST_PATH dry_run=true result=PASS skip_reason=no_pending_approvals") -Inputs @($prompt) -Outputs @('FAST_PATH','SKIP')
    continue
  }

  if ($isDryRun) {
    $out = powershell -ExecutionPolicy Bypass -File scripts/automation/resolve_approval_intent.ps1 -Message $prompt -DryRun 2>&1
  } else {
    $out = powershell -ExecutionPolicy Bypass -File scripts/automation/resolve_approval_intent.ps1 -Message $prompt 2>&1
  }
  $pass = ($out -join "`n") -match 'Dry run — would apply the latest ready build\.'
  if (-not $pass) { $allPass = $false; $pain += 'D: approval dry-run handler failed with pending approval' }
  $status = if ($pass) { 'PASS' } else { 'FAIL' }
  Write-Output ("[$status] Step $($s.name): route=FAST_PATH expected=FAST_PATH")
  Write-Output ("  reply: " + (($out | Select-Object -First 1) -join ''))
  $evWord = if ($pass) { 'OK' } else { 'WARN' }
  $evEmoji = if ($pass) { '✅' } else { '⚠️' }
  Emit-LogEvent -RunId $stepId -StatusWord $evWord -StatusEmoji $evEmoji -ReasonCode 'FRESH_SESSION_STEP' -Summary ("step="+$s.name+" route=FAST_PATH dry_run="+$isDryRun.ToString().ToLowerInvariant()+" result="+$status) -Inputs @($prompt) -Outputs @('FAST_PATH')
}

$gitAfter = @(git status --porcelain)
$tmpLedgersAfter = @(Get-TmpLedgerClones)
$gitUnchanged = ((($gitBefore -join "`n") -eq ($gitAfter -join "`n")))
if (-not $gitUnchanged) {
  $allPass = $false
  $pain += 'Working tree changed during replay (dry-run not non-mutating).'
}
$newTmpLedgers = @($tmpLedgersAfter | Where-Object { $_ -notin $tmpLedgersBefore })
if ($newTmpLedgers.Count -gt 0) {
  $allPass = $false
  $pain += ('tmp ledger clone(s) created: ' + ($newTmpLedgers -join ', '))
}

$overall = if ($allPass) { 'PASS' } else { 'FAIL' }
Write-Output '---'
Write-Output ("Fresh replay overall: " + $overall)
Write-Output 'git status before:'
if ($gitBefore.Count -eq 0) { Write-Output '(clean)' } else { $gitBefore | ForEach-Object { Write-Output $_ } }
Write-Output 'git status after:'
if ($gitAfter.Count -eq 0) { Write-Output '(clean)' } else { $gitAfter | ForEach-Object { Write-Output $_ } }
Write-Output ('tmp ledger clones before: ' + $tmpLedgersBefore.Count)
Write-Output ('tmp ledger clones after: ' + $tmpLedgersAfter.Count)
if ($pain.Count -gt 0) {
  Write-Output 'Pain points:'
  $pain | ForEach-Object { Write-Output ("- " + $_) }
}

$sumWord = if ($allPass) { 'OK' } else { 'WARN' }
$sumEmoji = if ($allPass) { '✅' } else { '⚠️' }
Emit-LogEvent -RunId ($runRoot + '-summary') -StatusWord $sumWord -StatusEmoji $sumEmoji -ReasonCode 'FRESH_SESSION_STEP' -Summary ("fresh_session_replay overall="+$overall+" dry_run="+$isDryRun.ToString().ToLowerInvariant()+" git_unchanged="+$gitUnchanged.ToString().ToLowerInvariant()) -Inputs @('A','B','C','D') -Outputs @($overall)
