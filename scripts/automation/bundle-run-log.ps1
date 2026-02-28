param(
  [switch]$QuietMode
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($true)
$OutputEncoding = [Console]::OutputEncoding

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$bridgeEnvFile = Join-Path $ROOT 'scripts\claude-bridge\.env'
$rootEnvFile = Join-Path $ROOT '.env'
$actionsLog = Join-Path $ROOT 'data\logs\actions.ndjson'
$logsDir = Join-Path $ROOT 'data\logs'
$stateDir = Join-Path $ROOT 'data\state'
$lastMsgPath = Join-Path $logsDir 'bundle-run-log.last.txt'
$payloadPath = Join-Path $logsDir 'bundle-run-log.payload.json'
$lastRunPath = Join-Path $stateDir 'bundle-last-run.txt'
$cutoffUtc = (Get-Date).ToUniversalTime().AddMinutes(-15)
$nowUtc = (Get-Date).ToUniversalTime()
$ts = Get-Date -Format 'h:mm tt'
$utf8Bom = New-Object System.Text.UTF8Encoding($true)

if (-not (Test-Path -LiteralPath $actionsLog)) { exit 0 }
if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }
if (-not (Test-Path -LiteralPath $stateDir)) { New-Item -ItemType Directory -Force -Path $stateDir | Out-Null }

# Dedup guard: skip if last send was <10 minutes ago
if (Test-Path -LiteralPath $lastRunPath) {
  try {
    $rawLast = (Get-Content -LiteralPath $lastRunPath -Raw -ErrorAction Stop).Trim()
    if (-not [string]::IsNullOrWhiteSpace($rawLast)) {
      $lastSentUtc = ([DateTimeOffset]::Parse($rawLast)).UtcDateTime
      if (($nowUtc - $lastSentUtc).TotalMinutes -lt 10) {
        exit 0
      }
    }
  } catch {}
}

function Get-EventTime([object]$ev) {
  try {
    if ($ev.ts_iso) { return ([DateTimeOffset]::Parse([string]$ev.ts_iso)).UtcDateTime }
  } catch {}
  return [DateTime]::MinValue
}

function E([int]$cp) {
  return [char]::ConvertFromUtf32($cp)
}

$EMOJI_BOT = E 0x1F916
$EMOJI_BACKTESTER = E 0x1F4C8
$EMOJI_LIBRARIAN = E 0x1F4DA
$EMOJI_PROMOTION = E 0x1F9EC
$EMOJI_REFINEMENT = E 0x1F501
$EMOJI_GRABBER = E 0x1F9F2
$EMOJI_LAB = E 0x1F9EA
$EMOJI_STRATEGIST = E 0x1F9E0
$EMOJI_KEEPER = E 0x1F5C3
$EMOJI_FIREWALL = E 0x1F6E1
$EMOJI_READER = E 0x1F517
$EMOJI_OK = E 0x2705
$EMOJI_WARN = E 0x26A0
$EMOJI_FAIL = E 0x274C
$EMOJI_BLOCKED = E 0x26D4
$EMOJI_INFO = E 0x2139

function Get-AgentEmoji([string]$agent) {
  $map = @{
    'oQ' = $EMOJI_BOT
    'Backtester' = $EMOJI_BACKTESTER
    'Librarian' = $EMOJI_LIBRARIAN
    'Promotion' = $EMOJI_PROMOTION
    'Refinement' = $EMOJI_REFINEMENT
    'Grabber' = $EMOJI_GRABBER
    'Lab' = $EMOJI_LAB
    'Strategist' = $EMOJI_STRATEGIST
    'Keeper' = $EMOJI_KEEPER
    'Firewall' = $EMOJI_FIREWALL
    'Reader' = $EMOJI_READER
  }
  if ($map.ContainsKey($agent)) { return $map[$agent] }
  return $EMOJI_BOT
}

function Get-StatusEmoji([string]$status) {
  $s = ([string]$status).ToUpperInvariant()
  $map = @{
    'OK' = $EMOJI_OK
    'WARN' = $EMOJI_WARN
    'FAIL' = $EMOJI_FAIL
    'BLOCKED' = $EMOJI_BLOCKED
    'INFO' = $EMOJI_INFO
    'PRODUCED' = $EMOJI_OK
  }
  if ($map.ContainsKey($s)) { return $map[$s] }
  return $EMOJI_INFO
}

function Get-StatusRank([string]$status) {
  switch (([string]$status).ToUpperInvariant()) {
    'FAIL' { return 5 }
    'BLOCKED' { return 4 }
    'WARN' { return 3 }
    'OK' { return 2 }
    'INFO' { return 1 }
    default { return 0 }
  }
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
  $status = ([string]$ev.status_word).ToUpperInvariant()
  $reason = [string]$ev.reason_code
  $action = [string]$ev.action

  if ($status -in @('WARN','FAIL','BLOCKED')) { return $true }
  if ($reason -match '(?i)SUMMARY') { return $true }
  if ($action -match '(?i)SUMMARY') { return $true }
  if (Test-ProducedEvent $ev) { return $true }
  return $false
}

function Get-RegexValue([string]$text, [string]$pattern) {
  $m = [regex]::Match($text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if ($m.Success) { return $m.Groups[1].Value }
  return $null
}

function Condense-Summary([string]$summary) {
  $s = ([string]$summary).Trim()
  if ([string]::IsNullOrWhiteSpace($s)) { return 'activity' }

  # Strip prefix like "Lab:" or "Batch:"
  $s = $s -replace '^[A-Za-z_\- ]+:\s*', ''

  $parts = New-Object System.Collections.Generic.List[string]

  $lib = Get-RegexValue $s 'active_library_size\s*=\s*(\d+)'
  if (-not $lib) { $lib = Get-RegexValue $s '\blib\s*=\s*(\d+)' }
  if ($lib) { $parts.Add("lib=$lib") }

  $starv = Get-RegexValue $s 'starvation(?:_cycles)?\s*=\s*(\d+)'
  if ($starv) { $parts.Add("starvation=$starv") }

  $drought = Get-RegexValue $s 'drought(?:_cycles)?\s*=\s*(\d+)'
  if ($drought) { $parts.Add("drought=$drought") }

  $runs = Get-RegexValue $s '\bruns\s*=\s*(\d+)'
  if ($runs) { $parts.Add("runs=$runs") }

  $fetched = Get-RegexValue $s '\bfetched\s*=\s*(\d+)'
  if ($fetched) { $parts.Add("fetched=$fetched") }

  $failed = Get-RegexValue $s '\bfailed\s*=\s*(\d+)'
  if ($failed) { $parts.Add("failed=$failed") }

  $variants = Get-RegexValue $s '\bvariants\s*=\s*(\d+)'
  if ($variants) { $parts.Add("variants=$variants") }

  if ($s -match '(?i)no variants') { $parts.Add('no variants') }
  if ($s -match '(?i)directive loop stalled') {
    $stall = Get-RegexValue $s '(\d+)\s*cycles?'
    if ($stall) { $parts.Add("directive-stall=$stall") } else { $parts.Add('directive stalled') }
  }

  if ($parts.Count -gt 0) {
    $uniq = @($parts | Select-Object -Unique)
    return (($uniq | Select-Object -First 4) -join ' ')
  }

  # Fallback: keep first sentence-ish chunk compact
  $plain = ($s -replace '\s+', ' ').Trim()
  if ($plain.Length -gt 72) { return ($plain.Substring(0, 72) + '…') }
  return $plain
}

function Test-AgentNoop([string]$bestStatus, [string]$summaryText, [array]$eventsForAgent) {
  $st = ([string]$bestStatus).ToUpperInvariant()
  if ($st -in @('WARN','FAIL','BLOCKED')) { return $false }
  if (@($eventsForAgent | Where-Object { Test-ProducedEvent $_ }).Count -gt 0) { return $false }

  $raw = ((@($eventsForAgent | ForEach-Object { [string]$_.summary }) -join ' ')).Trim()
  if ($raw -match '(?i)\bSKIPPED\b') { return $true }
  if ($summaryText -match '(?i)\bno variants\b') { return $true }

  $matches = [regex]::Matches([string]$summaryText, '=(-?\d+(?:\.\d+)?)')
  if ($matches.Count -gt 0) {
    $nonZero = $false
    foreach ($m in $matches) {
      try {
        if ([double]$m.Groups[1].Value -ne 0) { $nonZero = $true; break }
      } catch {}
    }
    if (-not $nonZero) { return $true }
  }

  return $false
}

$events = @()
Get-Content -LiteralPath $actionsLog -Encoding UTF8 -ErrorAction SilentlyContinue | ForEach-Object {
  $line = [string]$_
  if ([string]::IsNullOrWhiteSpace($line)) { return }
  try {
    $ev = $line | ConvertFrom-Json
    if ($null -eq $ev) { return }

    $evTime = Get-EventTime $ev
    if ($evTime -lt $cutoffUtc) { return }

    $runId = [string]$ev.run_id
    if (-not $runId.StartsWith('autopilot-')) { return }

    $events += $ev
  } catch {}
}

if ($events.Count -eq 0) { exit 0 }

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

$mainEvents = @($deduped | Where-Object { -not (Test-NoiseEvent $_) -and (Test-MainEvent $_) })
if ($mainEvents.Count -eq 0) { exit 0 }

$hasFail = (@($mainEvents | Where-Object { ([string]$_.status_word).ToUpperInvariant() -eq 'FAIL' }).Count -gt 0)
$hasBlocked = (@($mainEvents | Where-Object { ([string]$_.status_word).ToUpperInvariant() -eq 'BLOCKED' }).Count -gt 0)
$hasWarn = (@($mainEvents | Where-Object { ([string]$_.status_word).ToUpperInvariant() -eq 'WARN' }).Count -gt 0)
$hasProduced = (@($mainEvents | Where-Object { Test-ProducedEvent $_ }).Count -gt 0)

$overallStatus = 'OK'
if ($hasFail) { $overallStatus = 'FAIL' }
elseif ($hasBlocked) { $overallStatus = 'BLOCKED' }
elseif ($hasWarn) { $overallStatus = 'WARN' }
elseif ($hasProduced) { $overallStatus = 'PRODUCED' }

if ($QuietMode -and ($overallStatus -notin @('WARN','FAIL','BLOCKED','PRODUCED'))) { exit 0 }

$grouped = @($mainEvents | Group-Object agent | Sort-Object Name)
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add(("{0} oQ | codex 5.3 | {1} {2}" -f $EMOJI_BOT, $overallStatus, $ts))

$warnCount = 0
$failCount = 0
$blockedCount = 0
$visibleAgentCount = 0

foreach ($g in $grouped) {
  $agent = [string]$g.Name
  if ([string]::IsNullOrWhiteSpace($agent)) { continue }

  $eventsForAgent = @($g.Group | Sort-Object { Get-EventTime $_ })
  if ($eventsForAgent.Count -eq 0) { continue }

  $bestStatus = 'INFO'
  $bestRank = -1
  foreach ($ev in $eventsForAgent) {
    $st = ([string]$ev.status_word).ToUpperInvariant()
    $rank = Get-StatusRank $st
    if ($rank -gt $bestRank) {
      $bestRank = $rank
      $bestStatus = $st
    }

    # counts are computed after noop-filtering
  }

  if (([string]$bestStatus -eq 'OK') -and (@($eventsForAgent | Where-Object { Test-ProducedEvent $_ }).Count -gt 0)) {
    $bestStatus = 'PRODUCED'
  }

  $condensed = New-Object System.Collections.Generic.List[string]
  foreach ($ev in $eventsForAgent) {
    $c = Condense-Summary ([string]$ev.summary)
    if (-not [string]::IsNullOrWhiteSpace($c)) { $condensed.Add($c) }
  }

  $summaryText = 'activity'
  if ($condensed.Count -gt 0) {
    $uniq = @($condensed | Select-Object -Unique)
    $summaryText = (($uniq | Select-Object -First 3) -join '; ')
  }

  if (Test-AgentNoop -bestStatus $bestStatus -summaryText $summaryText -eventsForAgent $eventsForAgent) {
    continue
  }

  if ($bestStatus -eq 'WARN') { $warnCount++ }
  elseif ($bestStatus -eq 'FAIL') { $failCount++ }
  elseif ($bestStatus -eq 'BLOCKED') { $blockedCount++ }

  $agentEmoji = Get-AgentEmoji $agent
  $statusEmoji = Get-StatusEmoji $bestStatus
  $lines.Add(("{0} {1} | {2} {3}" -f $agentEmoji, $agent, $statusEmoji, $summaryText))
  $visibleAgentCount++
}

if ($visibleAgentCount -eq 0) { exit 0 }

if ($failCount -gt 0 -or $blockedCount -gt 0 -or $warnCount -gt 0) {
  if ($failCount -gt 0) { $lines.Add(("{0} failures={1}" -f (Get-StatusEmoji 'FAIL'), $failCount)) }
  if ($blockedCount -gt 0) { $lines.Add(("{0} blocked={1}" -f (Get-StatusEmoji 'BLOCKED'), $blockedCount)) }
  if ($warnCount -gt 0) { $lines.Add(("{0} warnings={1}" -f (Get-StatusEmoji 'WARN'), $warnCount)) }
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

$token = if ($env:TELEGRAM_BOT_TOKEN) { [string]$env:TELEGRAM_BOT_TOKEN } else { $null }
$chatId = if ($env:TELEGRAM_LOG_CHAT_ID) { [string]$env:TELEGRAM_LOG_CHAT_ID } else { $null }

if (Test-Path -LiteralPath $rootEnvFile) {
  Get-Content -LiteralPath $rootEnvFile -Encoding UTF8 | ForEach-Object {
    if (-not $token -and ($_ -match '^TELEGRAM_BOT_TOKEN=(.*)$')) { $token = $matches[1].Trim() }
    if (-not $chatId -and ($_ -match '^TELEGRAM_LOG_CHAT_ID=(.*)$')) { $chatId = $matches[1].Trim() }
  }
}

if (-not $token -and (Test-Path -LiteralPath $bridgeEnvFile)) {
  Get-Content -LiteralPath $bridgeEnvFile -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^CLAUDE_BRIDGE_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  }
}

if (-not $token -or -not $chatId) { exit 0 }

Add-Type -AssemblyName System.Web
$html = '<pre>' + [System.Web.HttpUtility]::HtmlEncode($message) + '</pre>'
$body = @{ chat_id = $chatId; text = $html; parse_mode = 'HTML' } | ConvertTo-Json -Compress

# Persist payload (UTF-8 with BOM) and read explicitly as UTF-8 for API call
[System.IO.File]::WriteAllText($payloadPath, $body, $utf8Bom)
$bodyUtf8 = Get-Content -LiteralPath $payloadPath -Encoding UTF8 -Raw

# Mark send time for 10-minute dedup guard
[System.IO.File]::WriteAllText($lastRunPath, $nowUtc.ToString('o'), $utf8Bom)

try {
  Invoke-RestMethod -Uri ("https://api.telegram.org/bot$token/sendMessage") -Method Post -Body $bodyUtf8 -ContentType 'application/json; charset=utf-8' | Out-Null
} catch {
  Write-Host "Send failed: $_"
}
