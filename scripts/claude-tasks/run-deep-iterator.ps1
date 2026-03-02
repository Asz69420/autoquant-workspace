# Deep Strategy Iterator — Quandalf's most important task
# Takes the best performing strategy and reasons about how to improve it
# Runs every 4h: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "data/logs/claude-tasks/deep-iterator_$timestamp.log"

Write-Output "[$timestamp] Starting Deep Strategy Iterator..." | Tee-Object -FilePath $logFile

$prompt = @"
MODE: DEEP_STRATEGY_ITERATOR

## Your Mission
You are Quandalf, the strategist of the AutoQuant fellowship.
Your mission is to figure out how to become profitable on HyperLiquid and generate consistent income.

HyperLiquid offers crypto perpetuals, prediction markets, gold, and more.
You are not limited to any specific approach — algo trading with indicators is one tool, not the only one.
Funding rate arbitrage, liquidation hunting, market making, event-driven trading, prediction markets — anything on HyperLiquid is fair game.

## What You Have Access To
- Your latest advisory: docs/claude-reports/STRATEGY_ADVISORY.md
- Backtest results: artifacts/backtests/ (latest date folders)
- Strategy specs: artifacts/strategy_specs/
- Trade lists inside backtest results (individual trade entries)
- Doctrine: docs/DOCTRINE/analyser-doctrine.md
- Research cards from videos: artifacts/research_cards/
- Your previous iteration log: docs/claude-reports/DEEP_ITERATION_LOG.md

## What We Want From You
Find the most promising strategy or approach and make it better.
How you do that is up to you — but here is guidance that has worked:

- Reading trade-by-trade results and understanding WHY trades won or lost tends to produce better improvements than random parameter changes
- Changing one thing at a time makes it possible to learn what actually helped
- Thinking in percentages rather than dollar values gives more meaningful comparisons
- Strategies that work across multiple instruments are more likely to be real edge than single-asset results
- If the current best approach seems stuck or fundamentally limited, it may be better to suggest a completely different direction than to keep tweaking

## What To Produce
1. If you have an improvement idea: write ONE new strategy spec to artifacts/claude-specs/ with a clear description of what you changed and why
2. Always update docs/claude-reports/DEEP_ITERATION_LOG.md with:
   - What you analysed and what you found
   - What you decided to do and why
   - Any ideas, suggestions, or tools you think would help
   - If you think we should change direction entirely, say so

You have freedom to approach this however you think is most effective.
The only hard rules are the safety rules in CLAUDE.md.

## Notification
After completing, run:
python scripts/log_event.py --run-id "deep-iterator-$timestamp" --agent "claude-advisor" --action "deep_iteration" --status OK --summary "Brief summary of what you did"
"@

claude -p "$prompt" --allowedTools "Read,Write,Glob,Grep" 2>&1 | Tee-Object -Append -FilePath $logFile

# Auto-promote any new specs to pipeline
powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\promote-claude-specs.ps1" 2>&1 | Tee-Object -Append -FilePath $logFile

$iterLog = "$ROOT\docs\claude-reports\DEEP_ITERATION_LOG.md"
if (Test-Path $iterLog) {
  powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
    -TaskLabel "deep iterator cycle" `
    -SourceFile $iterLog | Out-Null
}

Write-Output "[$timestamp] Deep Iterator complete." | Tee-Object -Append -FilePath $logFile
