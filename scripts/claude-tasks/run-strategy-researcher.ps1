$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

New-Item -ItemType Directory -Force -Path "$ROOT\docs\claude-reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\logs\claude-tasks" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "$ROOT\data\logs\claude-tasks\researcher_$timestamp.log"

$prompt = @"
MODE: STRATEGY_RESEARCHER

You are the Senior Quant Researcher for AutoQuant.
Identify meta-patterns across many autopilot cycles that the per-cycle Analyser misses.

READ these files:
1. All outcome notes in artifacts/outcomes/ (latest 30 files across all date folders)
2. The doctrine file: docs/DOCTRINE/analyser-doctrine.md
3. The latest 10 backtest results in artifacts/backtests/
4. Current signal templates: scripts/backtester/signal_templates.py
5. Previous advisory (if exists): docs/claude-reports/STRATEGY_ADVISORY.md

ANALYSE for:
- Which indicator families keep failing and should be abandoned
- Which templates produce zero trades (known bugs)
- Regime-specific patterns (strategies that work trending but die ranging)
- What has not been tried that the doctrine suggests
- Whether directives are being followed or ignored by the Strategist
- Overfit signals: high PF on few trades, wins clustered in one period

WRITE your advisory to:
docs/claude-reports/STRATEGY_ADVISORY.md

with sections:
- Executive Summary (2-3 sentences)
- Failing Patterns (stop iterating on these)
- Promising Directions (explore more)
- Template Health (per template: trades, avg PF, recommendation)
- Regime Insights
- Recommended Directives
- Doctrine Gaps

After writing, emit notification:
python scripts/log_event.py --agent "claude-advisor" --action "strategy_research" --status OK --summary "Advisory updated: [1-line key finding]"
"@

Write-Output "[$timestamp] Starting Strategy Researcher..." | Tee-Object -FilePath $logFile -Append
claude -p $prompt --allowedTools "Read,Write,Bash(python scripts/log_event.py*)" 2>&1 | Tee-Object -FilePath $logFile -Append
Write-Output "[$timestamp] Completed: $LASTEXITCODE" | Tee-Object -FilePath $logFile -Append