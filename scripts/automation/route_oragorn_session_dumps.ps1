[CmdletBinding()]
param(
  [string]$OragornWorkspacePath = 'C:\Users\Clamps\.openclaw\workspace-oragorn',
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Get-TsLocalAest([datetime]$UtcNow) {
  $aest = $UtcNow.AddHours(10)
  $day = $aest.ToString('dd').TrimStart('0')
  $month = $aest.ToString('MMM')
  $hour = $aest.ToString('hh').TrimStart('0')
  if ([string]::IsNullOrWhiteSpace($hour)) { $hour = '0' }
  $minute = $aest.ToString('mm')
  $ampm = $aest.ToString('tt')
  return ($day + ' ' + $month + ' ' + $hour + ':' + $minute + ' ' + $ampm + ' AEST')
}

function Write-ActionEvent([string]$RepoRoot, [string]$StatusWord, [string]$Summary, [string[]]$Inputs, [string[]]$Outputs) {
  $nowUtc = [datetime]::UtcNow
  $tsIso = $nowUtc.ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
  $tsFile = $nowUtc.ToString('yyyyMMddTHHmmssZ')
  $event = [ordered]@{
    ts_iso = $tsIso
    ts_local = Get-TsLocalAest -UtcNow $nowUtc
    ts_file = $tsFile
    run_id = ('route-oragorn-session-dumps-' + $tsFile)
    agent = 'Autopilot'
    model_id = 'openai-codex/gpt-5.3-codex'
    action = 'ORAGORN_SESSION_DUMP_ROUTED'
    status_word = $StatusWord
    status_emoji = $(if ($StatusWord -eq 'OK') { 'OK' } elseif ($StatusWord -eq 'WARN') { 'WARN' } else { 'INFO' })
    reason_code = 'ORAGORN_SESSION_DUMP_ROUTED'
    summary = $Summary
    inputs = @($Inputs)
    outputs = @($Outputs)
    attempt = $null
    error = $null
  }

  $actionsPath = Join-Path $RepoRoot 'data\logs\actions.ndjson'
  $actionsDir = Split-Path -Parent $actionsPath
  if (-not (Test-Path -LiteralPath $actionsDir)) {
    New-Item -ItemType Directory -Path $actionsDir -Force | Out-Null
  }
  ($event | ConvertTo-Json -Compress) | Add-Content -LiteralPath $actionsPath -Encoding UTF8
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$workspacePath = $OragornWorkspacePath
$memoryDir = Join-Path $workspacePath 'memory'
$destDir = Join-Path $workspacePath 'artifacts\session_dumps'

if (-not (Test-Path -LiteralPath $memoryDir)) {
  Write-Verbose ('No memory directory found at ' + $memoryDir)
  [pscustomobject]@{ moved = 0; dry_run = [bool]$DryRun; source = $memoryDir; destination = $destDir; files = @() } | ConvertTo-Json -Compress
  exit 0
}

$files = @(Get-ChildItem -LiteralPath $memoryDir -File -Filter '????-??-??-*.md' -ErrorAction SilentlyContinue)
if ($files.Count -eq 0) {
  Write-Verbose ('No Oragorn session dumps found in ' + $memoryDir)
  [pscustomobject]@{ moved = 0; dry_run = [bool]$DryRun; source = $memoryDir; destination = $destDir; files = @() } | ConvertTo-Json -Compress
  exit 0
}

if (-not $DryRun) {
  New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

$moves = @()
foreach ($f in $files) {
  $destPath = Join-Path $destDir $f.Name
  if (Test-Path -LiteralPath $destPath) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $ext = [System.IO.Path]::GetExtension($f.Name)
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 6)
    $destPath = Join-Path $destDir ($base + '-' + $suffix + $ext)
  }

  if (-not $DryRun) {
    Move-Item -LiteralPath $f.FullName -Destination $destPath -Force
  }

  $moves += [pscustomobject]@{
    from = $f.FullName
    to = $destPath
  }
}

$summary = ('Routed Oragorn session dumps: moved=' + $moves.Count + ' source=' + $memoryDir + ' destination=' + $destDir + ' dry_run=' + [bool]$DryRun)
$status = 'OK'
if ($DryRun) { $status = 'INFO' }

$inputPaths = @($files | ForEach-Object { $_.FullName })
$outputPaths = @($moves | ForEach-Object { $_.to })
Write-ActionEvent -RepoRoot $repoRoot -StatusWord $status -Summary $summary -Inputs $inputPaths -Outputs $outputPaths

[pscustomobject]@{
  moved = $moves.Count
  dry_run = [bool]$DryRun
  source = $memoryDir
  destination = $destDir
  files = $moves
} | ConvertTo-Json -Depth 5 -Compress
exit 0
