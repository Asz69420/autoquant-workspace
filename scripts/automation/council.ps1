[CmdletBinding()]
param(
  [string]$question,
  [int]$rounds = 5,
  [string]$name,
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
  --question  Required. Decision question for the council.
  --rounds    Optional. Max rounds (3-5, default: 5).
  --name      Optional. Friendly name shown in output.

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
      '--question' {
        if ($i + 1 -ge $RawArgs.Count) { throw 'Missing value for --question' }
        $script:question = $RawArgs[$i + 1]
        $i++
      }
      '--rounds' {
        if ($i + 1 -ge $RawArgs.Count) { throw 'Missing value for --rounds' }
        $script:rounds = [int]$RawArgs[$i + 1]
        $i++
      }
      '--name' {
        if ($i + 1 -ge $RawArgs.Count) { throw 'Missing value for --name' }
        $script:name = $RawArgs[$i + 1]
        $i++
      }
    }
  }
}

$rawArgs = @($MyInvocation.UnboundArguments)
if ($rawArgs.Count -gt 0) {
  Parse-LegacyArgs -RawArgs $rawArgs
}

if ($help) {
  Show-Usage
  exit 0
}

if ([string]::IsNullOrWhiteSpace($question)) {
  throw 'Missing required --question'
}

if ($rounds -lt 3 -or $rounds -gt 5) {
  throw '--rounds must be between 3 and 5'
}

$apiKey = $env:OPENROUTER_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) {
  throw 'OPENROUTER_API_KEY is required'
}

$baseUrl = if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_BASE_URL)) { 'https://openrouter.ai/api/v1' } else { $env:OPENROUTER_BASE_URL.TrimEnd('/') }
$endpoint = "$baseUrl/chat/completions"

$models = @(
  @{ id = 'openai-codex/gpt-5.3-codex'; label = 'GPT-5.3' },
  @{ id = 'opencode/minimax-m2.5'; label = 'MiniMax M2.5' }
)

function Invoke-ModelText {
  param(
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$Prompt,
    [double]$Temperature = 0.2
  )

  $body = @{
    model = $Model
    messages = @(
      @{ role = 'system'; content = 'You are part of a decision council. Be concrete, concise, and decision-oriented.' },
      @{ role = 'user'; content = $Prompt }
    )
    temperature = $Temperature
  } | ConvertTo-Json -Depth 8

  $headers = @{
    Authorization = "Bearer $apiKey"
    'Content-Type' = 'application/json'
  }

  $response = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -Body $body
  return [string]$response.choices[0].message.content
}

function Test-MaterialDisagreement {
  param(
    [Parameter(Mandatory = $true)][string]$A,
    [Parameter(Mandatory = $true)][string]$B,
    [Parameter(Mandatory = $true)][string]$QuestionText
  )

  $judgePrompt = @"
Question:
$QuestionText

Answer A:
$A

Answer B:
$B

Do these answers still materially disagree on recommended action?
Reply with exactly one word: YES or NO.
"@

  $judge = (Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $judgePrompt -Temperature 0.0).Trim().ToUpperInvariant()
  return $judge -eq 'YES'
}

$decisionName = if ([string]::IsNullOrWhiteSpace($name)) { 'Council Decision' } else { $name }

Write-Output "=== $decisionName ==="
Write-Output "Question: $question"
Write-Output "Max rounds: $rounds"
Write-Output ''

# Round 1: independent answers
$round1 = @{}
foreach ($m in $models) {
  $prompt = @"
Decision question:
$question

Provide your independent recommendation in this structure:
1) Recommended action
2) Confidence (High/Medium/Low)
3) Key risks
4) What would change your decision
5) Immediate next test
"@
  $round1[$m.label] = Invoke-ModelText -Model $m.id -Prompt $prompt
  Write-Output "[Round 1][$($m.label)]"
  Write-Output $round1[$m.label]
  Write-Output ''
}

# Round 2: cross-critique
$round2 = @{}
$round2['GPT-5.3'] = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt @"
Question:
$question

Your prior answer:
$($round1['GPT-5.3'])

Other model's answer:
$($round1['MiniMax M2.5'])

Critique the other model. Be specific about weak assumptions, missing risks, and where it is stronger than your view.
"@

$round2['MiniMax M2.5'] = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Prompt @"
Question:
$question

Your prior answer:
$($round1['MiniMax M2.5'])

Other model's answer:
$($round1['GPT-5.3'])

Critique the other model. Be specific about weak assumptions, missing risks, and where it is stronger than your view.
"@

Write-Output '[Round 2][GPT-5.3 critique]'
Write-Output $round2['GPT-5.3']
Write-Output ''
Write-Output '[Round 2][MiniMax M2.5 critique]'
Write-Output $round2['MiniMax M2.5']
Write-Output ''

# Round 3: revision
$current = @{}
$current['GPT-5.3'] = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt @"
Question:
$question

Your original answer:
$($round1['GPT-5.3'])

Critique received:
$($round2['MiniMax M2.5'])

Revise your position. Keep the same structure:
1) Recommended action
2) Confidence
3) Key risks
4) What would change your decision
5) Immediate next test
"@

$current['MiniMax M2.5'] = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Prompt @"
Question:
$question

Your original answer:
$($round1['MiniMax M2.5'])

Critique received:
$($round2['GPT-5.3'])

Revise your position. Keep the same structure:
1) Recommended action
2) Confidence
3) Key risks
4) What would change your decision
5) Immediate next test
"@

Write-Output '[Round 3][GPT-5.3 revised]'
Write-Output $current['GPT-5.3']
Write-Output ''
Write-Output '[Round 3][MiniMax M2.5 revised]'
Write-Output $current['MiniMax M2.5']
Write-Output ''

$materialDisagreement = Test-MaterialDisagreement -A $current['GPT-5.3'] -B $current['MiniMax M2.5'] -QuestionText $question
$lastRound = 3

for ($r = 4; $r -le $rounds -and $materialDisagreement; $r++) {
  $lastRound = $r

  $gptPrompt = @"
Question:
$question

Current GPT-5.3 answer:
$($current['GPT-5.3'])

Current MiniMax answer:
$($current['MiniMax M2.5'])

There is still material disagreement. Produce one more refined final proposal focused on convergence.
"@

  $miniPrompt = @"
Question:
$question

Current MiniMax answer:
$($current['MiniMax M2.5'])

Current GPT-5.3 answer:
$($current['GPT-5.3'])

There is still material disagreement. Produce one more refined final proposal focused on convergence.
"@

  $current['GPT-5.3'] = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $gptPrompt
  $current['MiniMax M2.5'] = Invoke-ModelText -Model 'opencode/minimax-m2.5' -Prompt $miniPrompt

  Write-Output "[Round $r][GPT-5.3]"
  Write-Output $current['GPT-5.3']
  Write-Output ''
  Write-Output "[Round $r][MiniMax M2.5]"
  Write-Output $current['MiniMax M2.5']
  Write-Output ''

  $materialDisagreement = Test-MaterialDisagreement -A $current['GPT-5.3'] -B $current['MiniMax M2.5'] -QuestionText $question
}

$stopReason = if ($materialDisagreement) { "Reached max rounds ($lastRound)" } else { "Early stop at round $lastRound (convergence reached)" }

$finalPrompt = @"
Decision question:
$question

Latest GPT-5.3 position:
$($current['GPT-5.3'])

Latest MiniMax M2.5 position:
$($current['MiniMax M2.5'])

Create a final synthesis block using this exact section order:
- Recommended action
- Confidence
- Key risks
- What would change decision
- Immediate next test

Keep it practical and concise.
"@

$final = Invoke-ModelText -Model 'openai-codex/gpt-5.3-codex' -Prompt $finalPrompt

Write-Output '=== Council Final Synthesis ==='
Write-Output "Stop reason: $stopReason"
Write-Output $final
