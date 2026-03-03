$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

New-Item -ItemType Directory -Force -Path "$ROOT\artifacts\claude-specs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\logs\claude-tasks" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "$ROOT\data\logs\claude-tasks\generator_$timestamp.log"

function Test-IsModelRateLimited([string]$text) {
  if ([string]::IsNullOrWhiteSpace($text)) { return $false }
  return ($text -match '(?i)rate\s*limit|too\s*many\s*requests|\b429\b|quota|overloaded|temporar(?:y|ily)\s+unavailable|cyber_policy_violation')
}

function Emit-RateLimitEvent([string]$status, [string]$summary) {
  try {
    python scripts/log_event.py --agent "claude-advisor" --action "model_rate_limit" --status $status --summary $summary | Out-Null
  } catch {}
}

function Invoke-ClaudeWithRetry([string]$promptText, [string]$logPath, [int]$maxAttempts = 2) {
  for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $out = & claude -p $promptText --allowedTools "Read,Write,Bash(python scripts/log_event.py*)" 2>&1 | Tee-Object -FilePath $logPath -Append | Out-String
    $exitCode = $LASTEXITCODE
    $isRateLimited = Test-IsModelRateLimited -text $out

    if ($exitCode -eq 0) {
      return 0
    }

    if ($isRateLimited -and $attempt -lt $maxAttempts) {
      Emit-RateLimitEvent -status "WARN" -summary "Generator rate-limited on attempt $attempt; backing off 90s and retrying."
      Start-Sleep -Seconds 90
      continue
    }

    if ($isRateLimited) {
      Emit-RateLimitEvent -status "FAIL" -summary "Generator blocked by model rate-limit/policy after retry."
    }

    return $exitCode
  }

  return 1
}

$prompt = @"
MODE: STRATEGY_GENERATOR

You are the Creative Strategist for AutoQuant.
Design novel strategy specs that are informed by Quandalf's evolving knowledge, not random indicator mashups.

READ these files:
1. docs/claude-reports/STRATEGY_ADVISORY.md (if exists)
2. docs/shared/QUANDALF_BRAIN.md (if exists)
3. docs/shared/QUANDALF_JOURNAL.md
4. docs/DOCTRINE/analyser-doctrine.md
5. Latest 5 outcome notes in artifacts/outcomes/
6. scripts/backtester/signal_templates.py
7. TEMPLATE_COMBOS in scripts/pipeline/emit_strategy_spec.py
8. One recent strategy spec in artifacts/strategy_specs/ (format reference)

DESIGN 2-3 creative strategy specs that:
- Use DIFFERENT templates from recent specs where possible
- Have clear edge hypotheses tied to regime behavior
- Include proper regime gates (ADX/trend structure where relevant)
- Follow exact JSON format of existing strategy specs
- Represent different underlying ideas (do not clone one concept)

FORMAT RULES:
- Each variant MUST have proper RoleFramework filters matching template
- Use templates from TEMPLATE_COMBOS: ema_crossover, rsi_pullback, macd_confirmation, supertrend_follow, bollinger_breakout, stochastic_reversal, ema_rsi_atr
- Include variants[] array with 2-3 variants per spec
- Set schema_version to "1.1"
- Set source to "claude-advisor"

WRITE each spec to:
artifacts/claude-specs/strategy-spec-[YYYYMMDD]-claude-[8chars].strategy_spec.json

After writing, emit notification:
python scripts/log_event.py --agent "claude-advisor" --action "strategy_generate" --status OK --summary "Generated [N] creative specs: [brief description of each]"
"@

Write-Output "[$timestamp] Starting Strategy Generator..." | Tee-Object -FilePath $logFile -Append
$taskExit = Invoke-ClaudeWithRetry -promptText $prompt -logPath $logFile -maxAttempts 2
Write-Output "[$timestamp] Completed: $taskExit" | Tee-Object -FilePath $logFile -Append

if ($taskExit -ne 0) {
  exit $taskExit
}

# Auto-promote generated specs into pipeline
powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\promote-claude-specs.ps1"

$journal = "$ROOT\docs\shared\QUANDALF_JOURNAL.md"
if (Test-Path $journal) {
  powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
    -TaskLabel "journal cycle" `
    -SourceFile $journal | Out-Null
} else {
  $recentSpecs = @(
    Get-ChildItem "$ROOT\artifacts\claude-specs\*.strategy_spec.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge (Get-Date).AddHours(-3) }
  )
  $summary = "Generated $($recentSpecs.Count) spec file(s) in this cycle."
  powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
    -TaskLabel "generator cycle" `
    -Summary $summary | Out-Null
}
