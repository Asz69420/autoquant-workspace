param()

$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location -LiteralPath $ROOT

$actionsPath = Join-Path $ROOT 'data\logs\actions.ndjson'
$statePath = Join-Path $ROOT 'data\state\quandalf_handoff_poll_state.json'
$lockDir = Join-Path $ROOT 'data\state\locks\quandalf_handoff_poll.lockdir'
$jobId = 'b6d07171-ab62-4038-a4ec-4a5ac7b3d0d7'

New-Item -ItemType Directory -Force -Path (Split-Path $statePath -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $lockDir -Parent) | Out-Null

if (Test-Path -LiteralPath $lockDir) {
  Write-Host 'Skip: handoff poll lock held.'
  exit 0
}
New-Item -ItemType Directory -Path $lockDir | Out-Null
try {
  $latestRunId = $null
  if (Test-Path -LiteralPath $actionsPath) {
    $rows = Get-Content -LiteralPath $actionsPath -Tail 4000 -Encoding UTF8
    foreach ($line in $rows) {
      try {
        $e = $line | ConvertFrom-Json
      } catch {
        continue
      }
      if ([string]$e.action -ne 'LAB_SUMMARY') { continue }
      $rid = [string]$e.run_id
      if ($rid -match '^(autopilot-\d+)') {
        $latestRunId = $matches[1]
      }
    }
  }

  if ([string]::IsNullOrWhiteSpace($latestRunId)) {
    Write-Host 'No completed Frodex run found.'
    exit 0
  }

  $lastTriggered = ''
  if (Test-Path -LiteralPath $statePath) {
    try {
      $st = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
      if ($st -and $st.last_triggered_run_id) {
        $lastTriggered = [string]$st.last_triggered_run_id
      }
    } catch {}
  }

  if ($lastTriggered -eq $latestRunId) {
    Write-Host ("No new run. latest=" + $latestRunId)
    exit 0
  }

  Write-Host ("New completed run detected: " + $latestRunId + " -> triggering quandalf-auto-execute")
  & openclaw cron run $jobId --timeout 120000 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw ('openclaw cron run failed with code ' + $LASTEXITCODE)
  }

  $state = @{
    last_triggered_run_id = $latestRunId
    updated_at = [DateTime]::UtcNow.ToString('o')
  }
  ($state | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $statePath -Encoding UTF8
  Write-Host ("Triggered for run " + $latestRunId)
}
finally {
  Remove-Item -LiteralPath $lockDir -Recurse -Force -ErrorAction SilentlyContinue
}
