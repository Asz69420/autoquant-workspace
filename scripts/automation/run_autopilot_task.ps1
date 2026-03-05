Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'

$lockPath = 'data\state\locks\autopilot_worker.lock'
if (Test-Path -LiteralPath $lockPath) {
  Write-Host 'Autopilot worker lock present; skipping this cycle cleanly.'
  exit 0
}

& '.\scripts\pipeline\autopilot_worker.ps1' -RepoHygieneMode FAIL -MaxBundlesPerRun 3

# Fire the Frodex card immediately after cycle completion (event-driven logging).
try {
  & '.\scripts\automation\bundle-run-log.ps1' -Pipeline frodex -WindowMinutes 16 | Out-Null
} catch {
  Write-Host ('WARN: immediate frodex log send failed: ' + $_.Exception.Message)
}
