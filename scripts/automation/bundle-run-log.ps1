param(
  [switch]$QuietMode
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($true)
$OutputEncoding = [Console]::OutputEncoding

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$envFile = Join-Path $ROOT 'scripts\claude-bridge\.env'
$actionsLog = Join-Path $ROOT 'data\logs\actions.ndjson'
$logsDir = Join-Path $ROOT 'data\logs'
$lastMsgPath = Join-Path $logsDir 'bundle-run-log.last.txt'
$payloadPath = Join-Path $logsDir 'bundle-run-log.payload.json'
$cutoffUtc = (Get-Date).ToUniversalTime().AddMinutes(-15)
$ts = Get-Date -Format 'h:mm tt'
$utf8Bom = New-Object System.Text.UTF8Encoding($true)

if (-not (Test-Path -LiteralPath $envFile)) { exit 0 }
if (-not (Test-Path -LiteralPath $actionsLog)) { exit 0 }
if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }

$events = @()
Get-Content -LiteralPath $actionsLog -ErrorAction SilentlyContinue | ForEach-Object {
  $line = [string]$_
  if ([string]::IsNullOrWhiteSpace($line)) { return }
  try {
    $ev = $line | ConvertFrom-Json
    if ($null -eq $ev) { return }

    $evTime = $null
    try {
      if ($ev.ts_iso) { $evTime = ([DateTimeOffset]::Parse([string]$ev.ts_iso)).UtcDateTime }
    } catch {}
    if ($null -eq $evTime) { return }
    if ($evTime -lt $cutoffUtc) { return }

    $runId = [string]$ev.run_id
    if (-not $runId.StartsWith('autopilot-')) { return }

    $events += $ev
  } catch {}
}

if ($events.Count -eq 0) { exit 0 }

function Get-EventTime([object]$ev) {
  try {
    if ($ev.ts_iso) { return ([DateTimeOffset]::Parse([string]$ev.ts_iso)).UtcDateTime }
  } catch {}
  return [DateTime]::MinValue
}

function Test-NoiseEvent([object]$ev) {
  $reason = [string]$ev.reason_code
  $summary = [string]$ev.summary
  if ($reason -match '(?i)AUDIT|DEBUG') { return $true }
  if ($summary -match '(?i)Telegram\s+send\s+payload') { return $true }
  return $false
}

function Test-ProducedEvent([object]$ev) {
  return (([string]$ev.action -match '(?i)PROMOT') -and ([string]$ev.summary -notmatch '(?i)SKIPPED'))
}

function Test-MainEvent([object]$ev) {
  $status = [string]$ev.status_word
  $reason = [string]$ev.reason_code
  $action = [string]$ev.action

  if ($status -in @('WARN','FAIL')) { return $true }
  if ($reason -match '(?i)SUMMARY') { return $true }
  if ($action -match '(?i)SUMMARY') { return $true }
  if (Test-ProducedEvent $ev) { return $true }

  return $false
}

$sorted = @($events | Sort-Object { Get-EventTime $_ })

# Dedupe by run_id + reason_code + status_word (keep earliest in sorted order)
$seen = New-Object 'System.Collections.Generic.HashSet[string]'
$deduped = @()
foreach ($ev in $sorted) {
  $kRun = if ($ev.run_id) { [string]$ev.run_id } else { '' }
  $kReason = if ($ev.reason_code) { [string]$ev.reason_code } else { '' }
  $kStatus = if ($ev.status_word) { [string]$ev.status_word } else { '' }
  $key = "$kRun|$kReason|$kStatus"
  if ($seen.Add($key)) { $deduped += $ev }
}

if ($deduped.Count -eq 0) { exit 0 }

$noiseCountsByAgent = @{}
$mainEvents = @()
foreach ($ev in $deduped) {
  if (Test-NoiseEvent $ev) {
    $agent = [string]$ev.agent
    if ([string]::IsNullOrWhiteSpace($agent)) { $agent = 'Unknown' }
    if (-not $noiseCountsByAgent.ContainsKey($agent)) { $noiseCountsByAgent[$agent] = 0 }
    $noiseCountsByAgent[$agent] = [int]$noiseCountsByAgent[$agent] + 1
    continue
  }

  if (Test-MainEvent $ev) {
    $mainEvents += $ev
  }
}

$hasErrors = (@($mainEvents | Where-Object { [string]$_.status_word -eq 'FAIL' }).Count -gt 0)
$hasWarns = (@($mainEvents | Where-Object { [string]$_.status_word -eq 'WARN' }).Count -gt 0)
$hasPromo = (@($mainEvents | Where-Object { Test-ProducedEvent $_ }).Count -gt 0)

$status = 'IDLE'
if ($hasErrors) { $status = 'ERRORS' }
elseif ($hasPromo) { $status = 'PRODUCED' }
elseif ($hasWarns) { $status = 'WARN' }

if ($QuietMode -and $status -eq 'IDLE') { exit 0 }
if ($mainEvents.Count -eq 0 -and $noiseCountsByAgent.Count -eq 0) { exit 0 }

$emoji = @{
  'IDLE' = '🔷'
  'PRODUCED' = '🟢'
  'WARN' = '🟡'
  'ERRORS' = '🔴'
}[$status]

$agentIcons = @{
  'Backtester' = '📊'
  'Librarian'  = '📚'
  'Promotion'  = '🚀'
  'Refinement' = '🔁'
  'Lab'        = '🧪'
  'oQ'         = '📋'
  'Strategist' = '🧠'
  'Reader'     = '📖'
  'Grabber'    = '📥'
  'Quandalf'   = '🟣'
  'Frodex'     = '🔷'
  'Logger'     = '🧾'
}

$groupedMain = @($mainEvents | Group-Object agent | Sort-Object Name)
$mainAgents = @($groupedMain | ForEach-Object { [string]$_.Name })
$noiseOnlyAgents = @($noiseCountsByAgent.Keys | Where-Object { $_ -notin $mainAgents } | Sort-Object)
$hiddenTotal = 0
foreach ($k in $noiseCountsByAgent.Keys) { $hiddenTotal += [int]$noiseCountsByAgent[$k] }

$lines = @()
$lines += "$emoji oQ LOG | $ts | $($mainEvents.Count) events | $status"
if ($hiddenTotal -gt 0) { $lines += "▫️ hidden noise: $hiddenTotal events" }
$lines += ''

foreach ($group in $groupedMain) {
  $agentName = [string]$group.Name
  if ([string]::IsNullOrWhiteSpace($agentName)) { $agentName = 'Unknown' }

  $icon = $agentIcons[$agentName]
  if (-not $icon) { $icon = '▫️' }

  $lines += "$icon $agentName"

  $collapsed = [ordered]@{}
  foreach ($ev in ($group.Group | Sort-Object { Get-EventTime $_ })) {
    $sum = [string]$ev.summary
    if (-not [string]::IsNullOrWhiteSpace($sum)) {
      $sum = $sum -replace '^[A-Za-z]+:\s*', ''
    }

    $sw = @{
      'OK'   = '✅'
      'WARN' = '⚠️'
      'FAIL' = '❌'
    }[[string]$ev.status_word]
    if (-not $sw) { $sw = '▪️' }

    $key = "$sw|$sum"
    if ($collapsed.Contains($key)) {
      $collapsed[$key].count = [int]$collapsed[$key].count + 1
    } else {
      $collapsed[$key] = [PSCustomObject]@{
        sw = $sw
        sum = $sum
        count = 1
      }
    }
  }

  foreach ($k in $collapsed.Keys) {
    $row = $collapsed[$k]
    if ([int]$row.count -gt 1) {
      $lines += " $($row.sw) $($row.sum) (x$($row.count))"
    } else {
      $lines += " $($row.sw) $($row.sum)"
    }
  }

  if ($noiseCountsByAgent.ContainsKey($agentName)) {
    $lines += " ▫️ $([int]$noiseCountsByAgent[$agentName]) audit/debug events (hidden)"
  }

  $lines += ''
}

foreach ($agentName in $noiseOnlyAgents) {
  $icon = $agentIcons[$agentName]
  if (-not $icon) { $icon = '▫️' }
  $lines += "$icon $agentName"
  $lines += " ▫️ $([int]$noiseCountsByAgent[$agentName]) audit/debug events (hidden)"
  $lines += ''
}

$message = ($lines -join "`n").TrimEnd()

# Telegram 4096-char guard
$maxLen = 4096
$suffix = '... truncated'
if ($message.Length -gt $maxLen) {
  $keep = $maxLen - $suffix.Length
  if ($keep -lt 0) { $keep = 0 }
  $message = $message.Substring(0, $keep) + $suffix
}

# Persist latest rendered message (UTF-8 with BOM)
[System.IO.File]::WriteAllText($lastMsgPath, $message, $utf8Bom)

$token = $null
$chatId = $null
Get-Content -LiteralPath $envFile | ForEach-Object {
  if ($_ -match '^CLAUDE_BRIDGE_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  if ($_ -match '^CLAUDE_BRIDGE_USER_ID=(.*)$') { $chatId = $matches[1].Trim() }
}

if (-not $token -or -not $chatId) { exit 0 }

Add-Type -AssemblyName System.Web
$html = '<pre>' + [System.Web.HttpUtility]::HtmlEncode($message) + '</pre>'
$body = @{ chat_id = $chatId; text = $html; parse_mode = 'HTML' } | ConvertTo-Json -Compress

# Persist payload (UTF-8 with BOM) and read explicitly as UTF-8 for API call
[System.IO.File]::WriteAllText($payloadPath, $body, $utf8Bom)
$bodyUtf8 = Get-Content -LiteralPath $payloadPath -Encoding UTF8 -Raw

try {
  Invoke-RestMethod -Uri ("https://api.telegram.org/bot$token/sendMessage") -Method Post -Body $bodyUtf8 -ContentType 'application/json; charset=utf-8' | Out-Null
} catch {
  Write-Host "Send failed: $_"
}
