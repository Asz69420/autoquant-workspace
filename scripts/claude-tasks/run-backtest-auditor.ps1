$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

New-Item -ItemType Directory -Force -Path "$ROOT\docs\claude-reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\logs\claude-tasks" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\state\locks" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logFile = "$ROOT\data\logs\claude-tasks\bt_auditor_$timestamp.log"
$sharedLockDir = "$ROOT\data\state\locks\quandalf_pipeline.lockdir"

if (Test-Path -LiteralPath $sharedLockDir) {
  try { python scripts/log_event.py --agent "claude-auditor" --action "backtest_audit" --status WARN --summary "Skipped: shared Quandalf pipeline lock is held by another task." | Out-Null } catch {}
  Write-Output "[$timestamp] Skipped: shared Quandalf pipeline lock held" | Tee-Object -FilePath $logFile -Append
  exit 0
}

New-Item -ItemType Directory -Path $sharedLockDir | Out-Null

try {

$prompt = @"
MODE: BACKTEST_AUDITOR

You are the Backtest Quality Auditor for AutoQuant.
Catch overfitting and data quality issues before bad strategies waste more iteration cycles.

READ these files:
1. All backtest results from last 48 hours in artifacts/backtests/
2. Corresponding trade lists in the same folders (*.trade_list.json)
3. docs/claude-reports/STRATEGY_ADVISORY.md (for context, if exists)

CHECK FOR:
1. OVERFITTING:
   PF above 2.0 with fewer than 30 trades,
   all winning trades clustered in one time period,
   win rate above 70 percent on trend-following strategies,
   huge profit from 1-2 trades carrying the whole result

2. DATA QUALITY:
   Zero-trade variants (template bug not strategy failure),
   identical results across different strategy specs (stale data reuse),
   max drawdown equals zero (impossible, indicates bug),
   negative trade counts or NaN values

3. REGIME BIAS:
   Strategy only profitable in one regime,
   all trades taken in low-volatility periods only,
   no trades during high-volatility events

WRITE your audit to:
docs/claude-reports/BACKTEST_AUDIT.md

with sections:
- Summary: N backtests reviewed, N flagged
- Overfit Suspects table (Spec, Variant, PF, Trades, Flag)
- Data Quality Issues
- Regime Analysis
- Recommendations

After writing, emit notification:
python scripts/log_event.py --agent "claude-auditor" --action "backtest_audit" --status OK --summary "Audited N backtests: N flagged for overfit, N data issues"
"@

Write-Output "[$timestamp] Starting Backtest Auditor..." | Tee-Object -FilePath $logFile -Append
claude -p $prompt --allowedTools "Read,Write,Bash(python scripts/log_event.py*)" 2>&1 | Tee-Object -FilePath $logFile -Append
Write-Output "[$timestamp] Completed: $LASTEXITCODE" | Tee-Object -FilePath $logFile -Append

$auditFile = "$ROOT\docs\claude-reports\BACKTEST_AUDIT.md"
if (Test-Path $auditFile) {
  powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\send-quandalf-cycle-summary.ps1" `
    -TaskLabel "audit cycle" `
    -SourceFile $auditFile | Out-Null
}
}
finally {
  Remove-Item -LiteralPath $sharedLockDir -Recurse -Force -ErrorAction SilentlyContinue
}