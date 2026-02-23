[CmdletBinding()]
param(
  [string]$question,
  [int]$rounds = 5,
  [string]$name,
  [ValidateSet('adaptive','low','medium','high')]
  [string]$reasoning = 'adaptive',
  [ValidateSet('short','medium')]
  [string]$verbosity = 'short',
  [int]$timeoutSec = 60,
  [switch]$help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-Usage {
  @"
Council mode (v1)

Usage:
  ./scripts/automation/council.ps1 --question """Should we do X?""" [--rounds 5] [--name "Decision Name"]

Inputs:
  --question   Required. Decision question for the council.
  --rounds     Optional. Max rounds (3-5, default: 5).
  --name       Optional. Friendly name shown in output.
  --reasoning  adaptive|low|medium|high (default: adaptive)
  --verbosity  short|medium (default: short)
  --timeoutSec Per-call HTTP timeout (default: 60)

Models:
  - openai-codex/gpt-5.3-codex
  - opencode/minimax-m2.5

Env required (either):
  OPENROUTER_API_KEY or OPENCODE_API_KEY
Optional env:
  OPENROUTER_BASE_URL (default: https://openrouter.ai/api/v1)
"@
}

function Parse-LegacyArgs {
  param([string[]]$RawArgs)

  for ($i = 0; $i -lt $RawArgs.Count; $i++) {
    switch ($RawArgs[$i]) {
      '--help' { $script:help = $true }
      '-h' { $script:help = $true }
      '--question' { $script:question = $RawArgs[++$i] }
      '--rounds' { $script:rounds = [int]$RawArgs[++$i] }
      '--name' { $script:name = $RawArgs[++$i] }
      '--reasoning' { $script:reasoning = $RawArgs[++$i] }
      '--verbosity' { $script:verbosity = $RawArgs[++$i] }
      '--timeoutSec' { $script:timeoutSec = [int]$RawArgs[++$i] }
    }
  }
}

$rawArgs = @($MyInvocation.UnboundArguments)
if ($rawArgs.Count -gt 0) { Parse-LegacyArgs -RawArgs $rawArgs }
if ($help) { Show-Usage; exit 0 }

if ([string]::IsNullOrWhiteSpace($question)) { throw 'Missing required --question' }
if ($rounds -lt 3 -or $rounds -gt 5) { throw '--rounds must be between 3 and 5' }
if ($reasoning -notin @('adaptive','low','medium','high')) { throw '--reasoning must be one of: adaptive, low, medium, high' }
if ($verbosity -notin @('short','medium')) { throw '--verbosity must be one of: short, medium' }
if ($timeoutSec -le 0) { throw '--timeoutSec must be > 0' }

function Load-DotEnvIfPresent {
  param([string[]]$Paths)
  foreach ($p in $Paths) {
    if (-not (Test-Path $p)) { continue }
    Get-Content $p | ForEach-Object {
      $line = $_.Trim()
      if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { return }
      $idx = $line.IndexOf('=')
      if ($idx -lt 1) { return }
      $k = $line.Substring(0, $idx).Trim()
      $v = $line.Substring($idx + 1).Trim().Trim('"')
      if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($k))) {
        [Environment]::SetEnvironmentVariable($k, $v)
      }
    }
  }
}

Load-DotEnvIfPresent -Paths @('.env', 'C:\Users\Clamps\.openclaw\.env')

$apiKey = if (-not [string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) { $env:OPENROUTER_API_KEY } elseif (-not [string]::IsNullOrWhiteSpace($env:OPENCODE_API_KEY)) { $env:OPENCODE_API_KEY } else { '' }
if ([string]::IsNullOrWhiteSpace($apiKey)) { throw 'Missing model API key. Set OPENROUTER_API_KEY or OPENCODE_API_KEY (or place it in .env).' }
$baseUrl = if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_BASE_URL)) { 'https://openrouter.ai/api/v1' } else { $env:OPENROUTER_BASE_URL.TrimEnd('/') }
$endpoint = "$baseUrl/chat/completions"

$models = @(
  @{ id = 'openai-codex/gpt-5.3-codex'; label = 'GPT-5.3' },
  @{ id = 'opencode/minimax-m2.5'; label = 'MiniMax M2.5' }
)

function Get-ReasoningMode {
  param([int]$Round)
  if ($reasoning -ne 'adaptive') { return $reasoning }
  if ($Round -ge 4) { return 'high' }
  return 'medium'
}

function Normalize-FailureReason {
  param([string]$Message, [Nullable[int]]$StatusCode = $null, [bool]$TimedOut = $false)

  $m = if ($null -eq $Message) { '' } else { $Message.ToLowerInvariant() }
  if ($StatusCode -in 401,403 -or $m -match 'unauthorized|forbidden|auth|invalid api key|authentication') { return 'AUTH_FAIL' }
  if ($TimedOut -or $m -match 'timeout|timed out|model unavailable|not found|provider unavailable|route unavailable|no route|overloaded') { return 'MODEL_UNAVAILABLE' }
  return 'TOOL_PATH_FAIL'
}

function Merge-FailureReason {
  param([string]$Current, [string]$Incoming)
  $rank = @{ 'NONE' = 0; 'TOOL_PATH_FAIL' = 1; 'MODEL_UNAVAILABLE' = 2; 'AUTH_FAIL' = 3 }
  $c = if ([string]::IsNullOrWhiteSpace($Current)) { 'NONE' } else { $Current }
  $i = if ([string]::IsNullOrWhiteSpace($Incoming)) { 'NONE' } else { $Incoming }
  if ($rank[$i] -gt $rank[$c]) { return $i }
  return $c
}

function Invoke-ModelText {
  param(
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$Prompt,
    [int]$Round = 1,
    [double]$Temperature = 0.2
  )

  $brevity = if ($verbosity -eq 'short') { 'Keep response under ~180 words, bullets preferred.' } else { 'Keep response concise and structured.' }
  $sys = "You are part of a decision council. Be concrete, concise, and decision-oriented. $brevity"

  $body = @{
    model = $Model
    messages = @(
      @{ role = 'system'; content = $sys },
      @{ role = 'user'; content = $Prompt }
    )
    temperature = $Temperature
    extra_body = @{ reasoning = @{ effort = (Get-ReasoningMode -Round $Round) } }
  } | ConvertTo-Json -Depth 10

  $headers = @{ Authorization = "Bearer $apiKey"; 'Content-Type' = 'application/json' }

  try {
    $response = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -Body $body -TimeoutSec $timeoutSec
    return @{ ok = $true; text = [string]$response.choices[0].message.content; reason = 'NONE'; statusCode = $null }
  }
  catch {
    $status = $null
    try { if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { $status = [int]$_.Exception.Response.StatusCode.value__ } } catch {}
    $msg = [string]$_.Exception.Message
    $timedOut = ($msg.ToLowerInvariant() -match 'timeout|timed out')
    $reason = Normalize-FailureReason -Message $msg -StatusCode $status -TimedOut:$timedOut
    return @{ ok = $false; text = ''; reason = $reason; statusCode = $status }
  }
}

function Ask-Both {
  param([string]$PromptA,[string]$PromptB,[int]$Round)
  $a = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $PromptA -Round $Round
  $b = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Prompt $PromptB -Round $Round
  return @{ gpt = $a; mini = $b }
}

function Test-MaterialDisagreement {
  param([string]$A,[string]$B,[string]$QuestionText,[int]$Round)
  if ([string]::IsNullOrWhiteSpace($A) -or [string]::IsNullOrWhiteSpace($B)) { return $true }
  $judgePrompt = @"
Question:
$QuestionText

Answer A:
$A

Answer B:
$B

Material disagreement exists only if recommended action or key risk posture is meaningfully different.
Reply exactly YES or NO.
"@
  $judge = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $judgePrompt -Round $Round -Temperature 0.0
  if (-not $judge.ok) { return $true }
  $jt = $judge.text.Trim().ToUpperInvariant()
  if ($jt -match '^YES\b') { return $true }
  if ($jt -match '^NO\b') { return $false }
  return $true
}

function SafeText([hashtable]$resp,[string]$label) {
  if ($resp.ok) { return $resp.text }
  return "[${label} unavailable: $($resp.reason)]"
}

function Build-LocalSynthesis {
  param(
    [string]$QuestionText,
    [string]$GptText,
    [string]$MiniText,
    [string]$StopReason,
    [bool]$Degraded
  )

  $warn = if ($Degraded) { 'Degraded mode: one or more model calls failed/timed out; synthesis based on available outputs.' } else { 'Normal mode.' }
  return @"
- Recommended action
Use the overlapping recommendation from both model outputs; if they diverge, choose the lower-risk option and run the immediate test below.

- Confidence
Medium ($warn)

- Key risks
- Hidden assumption mismatch between models
- Missing market/regime evidence for final commitment

- What would change decision
- New evidence that invalidates current assumptions
- Backtest/parity result that contradicts the recommendation

- Immediate next test
Run one constrained test that directly resolves the biggest disagreement from this council pass.
"@
}

function Has-RequiredSections([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  $required = @('Recommended action','Confidence','Key risks','What would change decision','Immediate next test')
  foreach ($r in $required) { if ($Text -notmatch [regex]::Escape($r)) { return $false } }
  return $true
}

$decisionName = if ([string]::IsNullOrWhiteSpace($name)) { 'Council Decision' } else { $name }
$runSuffix = ([guid]::NewGuid().ToString('N')).Substring(0, 6)
$councilRunId = "council-" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + "-" + $runSuffix
$script:LogEmitFailures = @()

function Emit-CouncilEvent {
  param(
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary
  )
  try {
    $args = @('scripts/log_event.py','--run-id',$councilRunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','council_run','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary,'--input','council.ps1')
    if (-not [string]::IsNullOrWhiteSpace($ReasonCode)) { $args += @('--reason-code', $ReasonCode) }
    python @args | Out-Null
    return $true
  }
  catch {
    $script:LogEmitFailures += ("${StatusWord}: " + [string]$_.Exception.Message)
    Write-Warning "Failed to emit council event [$StatusWord]: $([string]$_.Exception.Message)"
    return $false
  }
}

Write-Output "=== $decisionName ==="
Write-Output "Council run_id: $councilRunId"
Write-Output "Question: $question"
Write-Output "Max rounds: $rounds"
Write-Output "Reasoning: $reasoning"
Write-Output ''

$null = Emit-CouncilEvent -StatusWord 'START' -StatusEmoji '▶️' -ReasonCode 'COUNCIL_START' -Summary ("Council run started: " + $decisionName)

$failureReason = 'NONE'

# Canonical preflight probes (informational only; no path split)
$probePrompt = 'ping'
$probeG = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $probePrompt -Round 1 -Temperature 0.0
$probeM = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Prompt $probePrompt -Round 1 -Temperature 0.0
if (-not $probeG.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $probeG.reason }
if (-not $probeM.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $probeM.reason }

$gAvailable = $probeG.ok
$mAvailable = $probeM.ok
Write-Output "Preflight: GPT-5.3=$(if($gAvailable){'available'}else{'unavailable'}) | MiniMax M2.5=$(if($mAvailable){'available'}else{'unavailable'})"

$tmpl = @"
Decision question:
$question

Use this structure:
1) Recommended action
2) Confidence (High/Medium/Low)
3) Key risks
4) What would change your decision
5) Immediate next test
"@

$curG = '[GPT-5.3 unavailable: MODEL_UNAVAILABLE]'
$curM = '[MiniMax M2.5 unavailable: MODEL_UNAVAILABLE]'
$lastRound = 1
$stopReason = 'Reached max rounds'

# Round 1: both lanes (canonical path)
$r1 = Ask-Both -PromptA $tmpl -PromptB $tmpl -Round 1
if (-not $r1.gpt.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $r1.gpt.reason }
if (-not $r1.mini.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $r1.mini.reason }
$curG = SafeText $r1.gpt 'GPT-5.3'
$curM = SafeText $r1.mini 'MiniMax M2.5'
Write-Output '[Round 1][GPT-5.3]'; Write-Output $curG; Write-Output ''
Write-Output '[Round 1][MiniMax M2.5]'; Write-Output $curM; Write-Output ''

# Round 2: critiques (canonical path)
$gCrit = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Round 2 -Prompt @"
Question:
$question

Your prior answer:
$curG

Other model's answer:
$curM

Critique weak assumptions, missing risks, and strongest opposing points.
"@
$mCrit = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Round 2 -Prompt @"
Question:
$question

Your prior answer:
$curM

Other model's answer:
$curG

Critique weak assumptions, missing risks, and strongest opposing points.
"@
if (-not $gCrit.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $gCrit.reason }
if (-not $mCrit.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $mCrit.reason }
$critG = SafeText $gCrit 'GPT-5.3 critique'
$critM = SafeText $mCrit 'MiniMax critique'

# Round 3: revisions (canonical path)
$gRev = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Round 3 -Prompt @"
Question:
$question

Your original answer:
$curG

Critique received:
$critM

Revise using the 5-part structure.
"@
$mRev = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Round 3 -Prompt @"
Question:
$question

Your original answer:
$curM

Critique received:
$critG

Revise using the 5-part structure.
"@
if (-not $gRev.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $gRev.reason }
if (-not $mRev.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $mRev.reason }
$curG = SafeText $gRev 'GPT-5.3 revised'
$curM = SafeText $mRev 'MiniMax revised'
Write-Output '[Round 3][GPT-5.3 revised]'; Write-Output $curG; Write-Output ''
Write-Output '[Round 3][MiniMax M2.5 revised]'; Write-Output $curM; Write-Output ''

$material = Test-MaterialDisagreement -A $curG -B $curM -QuestionText $question -Round 3
$lastRound = 3
for ($r = 4; $r -le $rounds -and $material; $r++) {
  $lastRound = $r
  $g = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Round $r -Prompt "Question:`n$question`n`nCurrent GPT:`n$curG`n`nCurrent MiniMax:`n$curM`n`nIf disagreement remains, refine toward convergence."
  $m = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Round $r -Prompt "Question:`n$question`n`nCurrent MiniMax:`n$curM`n`nCurrent GPT:`n$curG`n`nIf disagreement remains, refine toward convergence."
  if (-not $g.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $g.reason }
  if (-not $m.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $m.reason }
  $curG = SafeText $g 'GPT-5.3'
  $curM = SafeText $m 'MiniMax M2.5'
  Write-Output "[Round $r][GPT-5.3]"; Write-Output $curG; Write-Output ''
  Write-Output "[Round $r][MiniMax M2.5]"; Write-Output $curM; Write-Output ''
  $material = Test-MaterialDisagreement -A $curG -B $curM -QuestionText $question -Round $r
}

if (-not $material) {
  $stopReason = "Early stop at round $lastRound (convergence reached)"
} else {
  $stopReason = "Reached max rounds ($lastRound)"
}

$finalPrompt = @"
Decision question:
$question

Latest GPT-5.3 position:
$curG

Latest MiniMax M2.5 position:
$curM

Create final synthesis sections:
- Recommended action
- Confidence
- Key risks
- What would change decision
- Immediate next test
"@

$finalResp = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $finalPrompt -Round ($lastRound + 1)
if (-not $finalResp.ok) { $failureReason = Merge-FailureReason -Current $failureReason -Incoming $finalResp.reason }
if ($script:LogEmitFailures.Count -gt 0) {
  $failureReason = Merge-FailureReason -Current $failureReason -Incoming 'TOOL_PATH_FAIL'
}

$executionMode = if ($failureReason -eq 'NONE') { 'normal' } else { 'degraded' }
$finalText = if ($finalResp.ok -and (Has-RequiredSections -Text $finalResp.text)) {
  $finalResp.text
} else {
  Build-LocalSynthesis -QuestionText $question -GptText $curG -MiniText $curM -StopReason $stopReason -Degraded ($executionMode -eq 'degraded')
}

Write-Output "Execution mode: $executionMode"
Write-Output "Failure reason: $failureReason"
Write-Output "Stop reason: $stopReason"
if ($script:LogEmitFailures.Count -gt 0) {
  Write-Output ('Log emit warnings: ' + ($script:LogEmitFailures -join '; '))
}
Write-Output $finalText

$terminalStatus = if ($executionMode -eq 'normal' -and $failureReason -eq 'NONE') { 'OK' } else { 'WARN' }
$terminalEmoji = if ($terminalStatus -eq 'OK') { '✅' } else { '⚠️' }
$terminalReason = if ($failureReason -eq 'NONE') { 'COUNCIL_OK' } else { $failureReason }
$null = Emit-CouncilEvent -StatusWord $terminalStatus -StatusEmoji $terminalEmoji -ReasonCode $terminalReason -Summary ("Council run finished: mode=" + $executionMode + ", reason=" + $failureReason + ", stop=" + $stopReason)
