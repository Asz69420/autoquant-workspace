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

Env required:
  OPENROUTER_API_KEY
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

$apiKey = $env:OPENROUTER_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) { throw 'OPENROUTER_API_KEY is required' }
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
    return @{ ok = $true; text = [string]$response.choices[0].message.content; error = $null }
  }
  catch {
    return @{ ok = $false; text = ''; error = $_.Exception.Message }
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
  return $judge.text.Trim().ToUpperInvariant() -eq 'YES'
}

function SafeText([hashtable]$resp,[string]$label) {
  if ($resp.ok) { return $resp.text }
  return "[${label} unavailable: $($resp.error)]"
}

$decisionName = if ([string]::IsNullOrWhiteSpace($name)) { 'Council Decision' } else { $name }
Write-Output "=== $decisionName ==="
Write-Output "Question: $question"
Write-Output "Max rounds: $rounds"
Write-Output "Reasoning: $reasoning"
Write-Output ''

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

$r1 = Ask-Both -PromptA $tmpl -PromptB $tmpl -Round 1
$curG = SafeText $r1.gpt 'GPT-5.3'
$curM = SafeText $r1.mini 'MiniMax M2.5'
Write-Output '[Round 1][GPT-5.3]'; Write-Output $curG; Write-Output ''
Write-Output '[Round 1][MiniMax M2.5]'; Write-Output $curM; Write-Output ''

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
$critG = SafeText $gCrit 'GPT-5.3 critique'
$critM = SafeText $mCrit 'MiniMax critique'

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
  $curG = SafeText $g 'GPT-5.3'
  $curM = SafeText $m 'MiniMax M2.5'
  Write-Output "[Round $r][GPT-5.3]"; Write-Output $curG; Write-Output ''
  Write-Output "[Round $r][MiniMax M2.5]"; Write-Output $curM; Write-Output ''
  $material = Test-MaterialDisagreement -A $curG -B $curM -QuestionText $question -Round $r
}

$stopReason = if ($material) { "Reached max rounds ($lastRound)" } else { "Early stop at round $lastRound (convergence reached)" }

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
If one model failed, include a brief degraded-mode warning.
"@
$finalResp = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $finalPrompt -Round ($lastRound + 1)
$finalText = SafeText $finalResp 'Final synthesis'

Write-Output '=== Council Final Synthesis ==='
Write-Output "Stop reason: $stopReason"
Write-Output $finalText
