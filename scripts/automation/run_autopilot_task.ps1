Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'

$lockPath = 'data\state\locks\autopilot_worker.lock'
if (Test-Path -LiteralPath $lockPath) {
  Write-Host 'Autopilot worker lock present; skipping this cycle cleanly.'
  exit 0
}

& '.\scripts\pipeline\autopilot_worker.ps1' -RepoHygieneMode FAIL

# Fire the Frodex card immediately after cycle completion (event-driven logging).
try {
  & '.\scripts\automation\bundle-run-log.ps1' -Pipeline frodex -WindowMinutes 16 | Out-Null
} catch {
  Write-Host ('WARN: immediate frodex log send failed: ' + $_.Exception.Message)
}

# Hyper mode chain authority is Quandalf -> Frodex (triggered from quandalf-auto-execute.sh).
# Do not trigger Quandalf handoff from Frodex completion here; this causes reversed flow/double logging.
