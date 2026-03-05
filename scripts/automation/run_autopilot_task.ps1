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

# Hyper mode: event-chain handoff (Frodex completion -> Quandalf trigger path) without schedule polling.
$hyperMode = $false
try {
  $flagsPath = '.\config\runtime_flags.json'
  if (Test-Path -LiteralPath $flagsPath) {
    $flags = Get-Content -LiteralPath $flagsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($flags -and $flags.PSObject.Properties.Name -contains 'hyperMode') {
      $hyperMode = [bool]$flags.hyperMode
    }
  }
} catch {
  $hyperMode = $false
}

if ($hyperMode) {
  try {
    $latestRunId = ''
    if (Test-Path -LiteralPath '.\data\logs\actions.ndjson') {
      $rows = Get-Content -LiteralPath '.\data\logs\actions.ndjson' -Tail 300 -Encoding UTF8
      foreach ($line in $rows) {
        try { $e = $line | ConvertFrom-Json } catch { continue }
        if ([string]$e.action -ne 'LAB_SUMMARY') { continue }
        $rid = [string]$e.run_id
        if ($rid -match '^(autopilot-\d+)') { $latestRunId = $matches[1] }
      }
    }

    if (-not [string]::IsNullOrWhiteSpace($latestRunId)) {
      & '.\scripts\automation\check_quandalf_handoff.ps1' -RunIdHint $latestRunId | Out-Null
    } else {
      & '.\scripts\automation\check_quandalf_handoff.ps1' | Out-Null
    }
  } catch {
    Write-Host ('WARN: hyper handoff trigger failed: ' + $_.Exception.Message)
  }
}
