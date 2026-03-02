$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

New-Item -ItemType Directory -Force -Path "$ROOT\artifacts\claude-specs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\logs\claude-tasks" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "$ROOT\data\logs\claude-tasks\generator_$timestamp.log"

$prompt = @"
MODE: STRATEGY_GENERATOR

You are the Creative Strategist for AutoQuant.
Design novel strategy specs that the rules-based Strategist cannot produce.

READ these files:
1. docs/claude-reports/STRATEGY_ADVISORY.md (if exists)
2. docs/DOCTRINE/analyser-doctrine.md
3. Latest 5 outcome notes in artifacts/outcomes/
4. scripts/backtester/signal_templates.py
5. TEMPLATE_COMBOS in scripts/pipeline/emit_strategy_spec.py
6. One recent strategy spec in artifacts/strategy_specs/ (as format reference)

DESIGN 2-3 creative strategy specs that:
- Use DIFFERENT templates from what recent specs used
- Have clear edge hypotheses (not random indicator combos)
- Include proper regime gates (ADX-based: trending vs ranging)
- Follow the exact JSON format of existing strategy specs
- Each spec tests a fundamentally different trading idea

FORMAT RULES:
- Each variant MUST have proper RoleFramework filters matching its template
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
claude -p $prompt --allowedTools "Read,Write,Bash(python scripts/log_event.py*)" 2>&1 | Tee-Object -FilePath $logFile -Append
Write-Output "[$timestamp] Completed: $LASTEXITCODE" | Tee-Object -FilePath $logFile -Append

# Auto-promote generated specs into pipeline
powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\promote-claude-specs.ps1"

$recentSpecs = @(
  Get-ChildItem "$ROOT\artifacts\claude-specs\*.strategy_spec.json" -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -ge (Get-Date).AddHours(-3) }
)
$summary = "Generated $($recentSpecs.Count) spec file(s) in this cycle."
powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
  -TaskLabel "generator cycle" `
  -Summary $summary | Out-Null