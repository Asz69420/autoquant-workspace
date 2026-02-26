param(
  [string]$WorkerScriptPath = 'scripts/pipeline/autopilot_worker.ps1',
  [string[]]$WorkerArgs = @('-RunYouTubeWatcher','-RunTVCatalogWorker','-MaxBundlesPerRun','3','-MaxRefinementsPerRun','1')
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repoRoot

$runId = 'lab-task-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$startedAt = [DateTime]::UtcNow.ToString('o')
$logDir = Join-Path $repoRoot 'artifacts/logs/lab_runs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$outPath = Join-Path $logDir ($runId + '.out.txt')
$errPath = Join-Path $logDir ($runId + '.err.txt')
$metaPath = Join-Path $logDir ($runId + '.meta.json')

$exitCode = 0
$launchFail = $false

try {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'powershell.exe'
  $args = @('-ExecutionPolicy','Bypass','-File',$WorkerScriptPath) + $WorkerArgs
  $psi.Arguments = ($args -join ' ')
  $psi.WorkingDirectory = $repoRoot
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  if (-not $proc.Start()) { throw 'Failed to launch lab worker process' }

  $stdout = $proc.StandardOutput.ReadToEnd()
  $stderr = $proc.StandardError.ReadToEnd()
  $proc.WaitForExit()
  $exitCode = [int]$proc.ExitCode

  Set-Content -Path $outPath -Value $stdout -Encoding utf8
  Set-Content -Path $errPath -Value $stderr -Encoding utf8
} catch {
  $launchFail = $true
  $exitCode = if ($exitCode -ne 0) { $exitCode } else { 1 }
  $msg = [string]$_.Exception.Message
  Set-Content -Path $outPath -Value '' -Encoding utf8
  Set-Content -Path $errPath -Value ("LAUNCH_FAIL: " + $msg) -Encoding utf8
}

$finishedAt = [DateTime]::UtcNow.ToString('o')
$meta = [ordered]@{
  run_id = $runId
  started_at = $startedAt
  finished_at = $finishedAt
  exit_code = $exitCode
  launch_failed = $launchFail
  out_path = ($outPath.Replace('\\','/'))
  err_path = ($errPath.Replace('\\','/'))
}
($meta | ConvertTo-Json -Depth 5) | Set-Content -Path $metaPath -Encoding utf8

if ($exitCode -ne 0 -or $launchFail) {
  try {
    python scripts/log_event.py --run-id $runId --agent oQ --model-id openai-codex/gpt-5.3-codex --action LAB_SCHED_FAIL --status-word FAIL --status-emoji FAIL --reason-code LAB_SCHED_FAIL --summary ("Lab scheduled run failed: exit=" + $exitCode + " (see err file)") --outputs ($errPath.Replace('\\','/')) ($outPath.Replace('\\','/')) 2>$null | Out-Null
  } catch {}
  exit $exitCode
}

exit 0
