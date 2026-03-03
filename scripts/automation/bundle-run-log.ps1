# Bundled Run Log — one photo+caption per pipeline cycle to LOG CHANNEL
# Default mode is Frodex (15-min lab loop). Optional Quandalf mode for Claude windows.

param(
  [ValidateSet('frodex','quandalf','oragorn')]
  [string]$Pipeline = 'frodex',
  [int]$WindowMinutes = 16
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$mode = $Pipeline.ToLowerInvariant()

# --- Config from .env ---
$wsEnv = "$ROOT\.env"
if (-not (Test-Path $wsEnv)) { Write-Host "No workspace .env"; exit 1 }

$token = $null
$logBotToken = $null
$logChannel = $null
Get-Content $wsEnv | ForEach-Object {
  if ($_ -match '^TELEGRAM_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  if ($_ -match '^TELEGRAM_LOG_BOT_TOKEN=(.*)$') { $logBotToken = $matches[1].Trim() }
  if ($_ -match '^TELEGRAM_LOG_CHAT_ID=(.*)$') { $logChannel = $matches[1].Trim() }
}
if (-not $token) { Write-Host "Missing bot token"; exit 1 }
if (-not $logChannel) { Write-Host "Missing log channel ID"; exit 1 }
$telegramSendToken = if (-not [string]::IsNullOrWhiteSpace($logBotToken)) { $logBotToken } else { $token }

# --- Read events from recent window ---
$logPath = "$ROOT\data\logs\actions.ndjson"
if (-not (Test-Path $logPath)) { Write-Host "No action log"; exit 0 }

$effectiveWindow = if ($WindowMinutes -lt 1) { 1 } else { $WindowMinutes }
$cutoff = (Get-Date).AddMinutes(-1 * $effectiveWindow).ToUniversalTime()
$tailLines = switch ($mode) {
  'oragorn' { 5000 }
  'quandalf' { 1500 }
  default { 1200 }
}
$events = @()
foreach ($line in (Get-Content $logPath -Encoding UTF8 -Tail $tailLines)) {
  try {
    $entry = $line | ConvertFrom-Json
    $tsRaw = if ($entry.ts_iso) { $entry.ts_iso } elseif ($entry.ts) { $entry.ts } else { $null }
    if (-not $tsRaw) { continue }
    try { $ts = [DateTime]::Parse($tsRaw).ToUniversalTime() } catch { continue }
    if ($ts -ge $cutoff) { $events += $entry }
  } catch { continue }
}
if ($events.Count -eq 0) {
  Write-Host "No events in window (sending heartbeat bundle)"
}

# --- Filter noise + pipeline ownership ---
$mainEvents = @($events | Where-Object {
  $a = if ($_.agent) { [string]$_.agent } else { "" }
  $act = if ($_.action) { [string]$_.action } else { "" }
  if (($a -eq "Logger") -or ($act -match "AUDIT|DIAG")) { return $false }

  if ($mode -eq 'quandalf') {
    # Quandalf-owned stream (Claude strategist tasks)
    return ($a -match '(?i)claude|quandalf')
  }

  if ($mode -eq 'oragorn') {
    # Oragorn commander stream
    return ($a -match '(?i)^oragorn$')
  }

  # Frodex-owned stream: explicitly exclude Claude/Quandalf/Oragorn entries
  return -not ($a -match '(?i)claude|quandalf|oragorn')
})
$noEventsWindow = $false
if ($mainEvents.Count -eq 0) {
  $noEventsWindow = $true
  Write-Host "No meaningful events for pipeline=$mode (sending heartbeat bundle)"
}

# Suppress sync-only windows (prevents duplicate standalone repo-sync style pings)
if (-not $noEventsWindow -and $mode -eq 'frodex') {
  $nonRepoEvents = @($mainEvents | Where-Object { [string]$_.action -ne 'REPO_HYGIENE_GATE' })
  $repoInfoOnly = @($mainEvents | Where-Object { ([string]$_.action -eq 'REPO_HYGIENE_GATE') -and ([string]$_.status_word -eq 'INFO') })
  if ($nonRepoEvents.Count -eq 0 -and $repoInfoOnly.Count -gt 0) {
    Write-Host "Skip send: repo-sync hygiene-only window"
    exit 0
  }
}

$oragornSubagentCompletionEvents = @()
$isOragornSubagentNoteOnly = $false
if ($mode -eq 'oragorn') {
  $oragornSubagentCompletionEvents = @(
    $mainEvents |
    Where-Object {
      $a = [string]$_.action
      $s = [string]$_.summary
      ((@('SUBAGENT_FINISH','SUBAGENT_FAIL') -contains $a) -and ($s -match '^Sub-agent completed:\s+.+\.jsonl\.deleted\.'))
    }
  )

  $nonCompletionEvents = @(
    $mainEvents |
    Where-Object {
      $a = [string]$_.action
      $s = [string]$_.summary
      -not ((@('SUBAGENT_FINISH','SUBAGENT_FAIL') -contains $a) -and ($s -match '^Sub-agent completed:\s+.+\.jsonl\.deleted\.'))
    }
  )

  $isOragornSubagentNoteOnly = (
    $oragornSubagentCompletionEvents.Count -gt 0 -and (
      $nonCompletionEvents.Count -eq 0 -or
      $WindowMinutes -le 2
    )
  )
}

function Get-EventUtcTimestamp {
  param($Event)
  $raw = if ($Event.ts_iso) { [string]$Event.ts_iso } elseif ($Event.ts) { [string]$Event.ts } else { $null }
  if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
  try { return [DateTime]::Parse($raw).ToUniversalTime() } catch { return $null }
}

function Format-CompactDuration {
  param([TimeSpan]$Duration)
  if ($Duration.TotalSeconds -lt 0) { $Duration = [TimeSpan]::Zero }

  $totalSeconds = [int][Math]::Floor($Duration.TotalSeconds)
  $hours = [int][Math]::Floor($totalSeconds / 3600)
  $minutes = [int][Math]::Floor(($totalSeconds % 3600) / 60)
  $seconds = $totalSeconds % 60

  if ($hours -gt 0) { return ('{0}h {1:00}m' -f $hours, $minutes) }
  if ($minutes -gt 0) { return ('{0}m {1}s' -f $minutes, $seconds) }
  return ('{0}s' -f $seconds)
}

$eventTimestamps = @($mainEvents | ForEach-Object { Get-EventUtcTimestamp $_ } | Where-Object { $_ -ne $null } | Sort-Object)
$durationLabel = '<1s'
if ($eventTimestamps.Count -ge 2) {
  $windowDuration = ($eventTimestamps[-1] - $eventTimestamps[0])
  if ($windowDuration.TotalSeconds -eq 0) {
    $durationLabel = '<1s'
  } else {
    $durationLabel = Format-CompactDuration $windowDuration
  }
}

# --- Banner selection ---
$primaryAgent = if ($mode -eq 'quandalf') { "quandalf" } elseif ($mode -eq 'oragorn') { "oragorn" } else { "frodex" }

$bannerPath = $null
$bannerDir = "$ROOT\assets\banners"
if (Test-Path $bannerDir) {
  $bannerFiles = Get-ChildItem $bannerDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^${primaryAgent}_banner\." }
  if ($bannerFiles) { $bannerPath = $bannerFiles[0].FullName }
}

# --- Extract metrics ---
$grabbed = 0; $grabFailed = 0
$btRuns = 0; $btExecuted = 0; $btSkipped = 0
$promoted = 0
$refined = 0
$librarySize = 0; $libNew = 0; $libLessons = 0
$dirNotes = 0; $dirVariants = 0; $dirExplore = 0
$ingested = 0; $errors = 0
$insightNew = 0
$stall = 0; $starvation = 0
$warnings = @()
$forwardRuns = 0; $forwardEntries = 0; $forwardCloses = 0; $forwardSignalEvals = 0; $forwardOpenPositions = 0
$delegated = 0; $spawned = 0; $completed = 0; $failed = 0; $totalActions = 0

foreach ($e in $mainEvents) {
  $sum = if ($e.summary) { $e.summary } else { "" }
  $act = if ($e.action) { $e.action } else { "" }
  $stat = if ($e.status_word) { $e.status_word.ToUpper() } else { "OK" }

  switch ($act) {
    "GRABBER_SUMMARY" {
      if ($sum -match 'fetched=(\d+)') { $grabbed = [int]$matches[1] }
      if ($sum -match 'failed=(\d+)') { $grabFailed = [int]$matches[1] }
    }
    "BATCH_BACKTEST_SUMMARY" {
      if ($sum -match 'runs=(\d+)') { $btRuns = [int]$matches[1] }
      if ($sum -match 'executed=(\d+)') { $btExecuted = [int]$matches[1] }
      if ($sum -match 'skipped=(\d+)') { $btSkipped = [int]$matches[1] }
    }
    "LIBRARIAN_SUMMARY" {
      if ($sum -match 'run=(\d+)') { $librarySize = [int]$matches[1] }
      if ($sum -match 'new=(\d+)') { $libNew = [int]$matches[1] }
      if ($sum -match 'lessons=(\d+)') { $libLessons = [int]$matches[1] }
    }
    "PROMOTION_SUMMARY" {
      if ($sum -match 'variants=(\d+)') { $promoted = [int]$matches[1] }
    }
    "REFINEMENT_SUMMARY" {
      if ($sum -match 'iters=(\d+)') { $refined = [int]$matches[1] }
    }
    "DIRECTIVE_LOOP_SUMMARY" {
      if ($sum -match 'notes=(\d+)') { $dirNotes = [int]$matches[1] }
      if ($sum -match 'directive_variants=(\d+)') { $dirVariants = [int]$matches[1] }
      if ($sum -match 'exploration_variants=(\d+)') { $dirExplore = [int]$matches[1] }
    }
    "DIRECTIVE_LOOP_STALL_WARN" {
      if ($sum -match '(\d+)\s*cycle') { $stall = [int]$matches[1] }
    }
    "LAB_STARVATION_WARN" {
      if ($sum -match 'starvation[=:\s]+(\d+)') { $starvation = [int]$matches[1] }
      elseif ($sum -match '(\d+)') { $starvation = [int]$matches[1] }
    }
    "LAB_SUMMARY" {
      if ($sum -match 'ingested=(\d+)') { $ingested = [int]$matches[1] }
      if ($sum -match 'errors=(\d+)') { $errors = [int]$matches[1] }
      if ($sum -match 'starvation[=:\s]+(\d+)') { $starvation = [int]$matches[1] }
    }
    "INSIGHT_SUMMARY" {
      if ($sum -match 'new_processed=(\d+)') { $insightNew = [int]$matches[1] }
    }
    "DIRECTIVE_GEN_FAIL" { $errors++ }
  }

  if ($sum -match 'stall.*?(\d+)\s*cycle' -and $stall -eq 0) { $stall = [int]$matches[1] }
  if ($stat -in @("WARN", "FAIL", "BLOCKED")) {
    $reasonCode = if ($e.reason_code) { ([string]$e.reason_code).ToUpper() } else { "UNKNOWN" }
    $reasonLabel = switch ($reasonCode) {
      "DIRECTIVE_LOOP_SUMMARY" { "No new strategy variants this cycle" }
      "DIRECTIVE_GEN_FAIL" { "Strategy generation failure" }
      "REFINEMENT_SUMMARY" { "Refinement step warning" }
      "BATCH_BACKTEST_SUMMARY" { "Backtest stage warning" }
      "LAB_SUMMARY" { "Pipeline stage warning" }
      default {
        $txt = ($reasonCode -replace '_', ' ').ToLowerInvariant()
        if ($txt.Length -gt 0) { $txt.Substring(0,1).ToUpper() + $txt.Substring(1) } else { "General warning" }
      }
    }

    $agentName = if ($e.agent) { [string]$e.agent } else { "Pipeline" }
    $wKey = "${agentName}: $reasonLabel"
    if ($reasonCode -notmatch "STALL|STARVATION") { $warnings += $wKey }
  }
}

# --- Forward-test bridge (data/forward) ---
if ($mode -eq 'frodex') {
  $forwardLogPath = "$ROOT\data\forward\FORWARD_LOG.ndjson"
  if (Test-Path $forwardLogPath) {
    foreach ($line in (Get-Content $forwardLogPath -Encoding UTF8 -Tail 1200)) {
      try {
        $entry = $line | ConvertFrom-Json
        if (-not $entry.ts_iso) { continue }
        $fts = [DateTime]::Parse([string]$entry.ts_iso).ToUniversalTime()
        if ($fts -lt $cutoff) { continue }

        $evt = [string]$entry.event
        switch ($evt) {
          'RUN_OK' { $forwardRuns++ }
          'POSITION_OPEN' { $forwardEntries++ }
          'POSITION_CLOSE' { $forwardCloses++ }
          'SIGNAL_EVAL' { $forwardSignalEvals++ }
        }
      } catch { continue }
    }
  }

  $forwardStatePath = "$ROOT\data\forward\PAPER_POSITIONS.json"
  if (Test-Path $forwardStatePath) {
    try {
      $st = Get-Content $forwardStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
      if ($st -and $st.lanes) {
        foreach ($lane in $st.lanes.PSObject.Properties) {
          $v = $lane.Value
          if ($v -and $v.open_position) { $forwardOpenPositions++ }
        }
      }
    } catch {}
  }
}

# --- Build message ---
$hasErrors = $errors -gt 0
$hasWarnings = ($stall -gt 5) -or ($starvation -gt 10) -or ($warnings.Count -gt 0)
$statusTag = if ($hasErrors) { "FAIL" } elseif ($hasWarnings) { "WARN" } else { "OK" }
$statusIcon = switch ($statusTag) {
  "OK" { "✅" }
  "WARN" { "⚠️" }
  "FAIL" { "❌" }
}

$agentLabel = if ($mode -eq 'quandalf') { "Quandalf" } elseif ($mode -eq 'oragorn') { "Oragorn" } else { "Frodex" }

# Model label for header (abbrev, no spaces: GPT5.3 / OPUS4.6)
$modelLabel = ''
$modelBuckets = @($mainEvents | ForEach-Object { [string]$_.model_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -ne 'system' } | Group-Object | Sort-Object Count -Descending)
if ($modelBuckets.Count -gt 0) {
  $modelRaw = [string]$modelBuckets[0].Name

  if ($modelRaw -match '(?i)gpt[-_ ]?5\.3') { $modelLabel = 'GPT5.3' }
  elseif ($modelRaw -match '(?i)opus[-_ ]?4\.6|opus[-_ ]?4[-_ ]?6') { $modelLabel = 'OPUS4.6' }
  elseif ($modelRaw -match '(?i)sonnet[-_ ]?4\.5|sonnet[-_ ]?4[-_ ]?5') { $modelLabel = 'SONNET4.5' }
  elseif ($modelRaw -match '(?i)haiku[-_ ]?3\.5|haiku[-_ ]?3[-_ ]?5') { $modelLabel = 'HAIKU3.5' }
  else {
    # Generic formatter for any model id: provider/model-name-version -> MODELNAMEVERSION
    $tail = if ($modelRaw -match '/') { ($modelRaw -split '/')[-1] } else { $modelRaw }
    $tail = $tail -replace '(?i)-codex', ''
    $tail = $tail.ToUpperInvariant()
    $tail = $tail -replace '[ _]', ''
    $tail = $tail -replace '-', ''
    if ($tail.Length -gt 14) { $tail = $tail.Substring(0, 14) }
    if (-not [string]::IsNullOrWhiteSpace($tail)) { $modelLabel = $tail }
  }
}

$headerParts = @($statusIcon, $agentLabel, '⏱', $durationLabel)
if (-not [string]::IsNullOrWhiteSpace($modelLabel)) { $headerParts += $modelLabel }
$headerLine = ($headerParts -join ' ').Trim()

$lines = @()
$lines += $headerLine

$strategyGenerateCount = @($mainEvents | Where-Object { [string]$_.action -eq 'strategy_generate' }).Count
$strategyResearchCount = @($mainEvents | Where-Object { [string]$_.action -eq 'strategy_research' }).Count
$doctrineSynthesisCount = @($mainEvents | Where-Object { [string]$_.action -eq 'doctrine_synthesis' }).Count
$backtestAuditCount = @($mainEvents | Where-Object { [string]$_.action -eq 'backtest_audit' }).Count
$totalStrictRuns = $strategyGenerateCount + $strategyResearchCount + $doctrineSynthesisCount + $backtestAuditCount

if ($mode -eq 'quandalf') {
  $lines += "○───activity─────────────────────"
  $lines += "Research cycles: $strategyResearchCount"
  $lines += "Strategy drafts: $strategyGenerateCount"
  $lines += "Doctrine updates: $doctrineSynthesisCount"
  $lines += "Audits: $backtestAuditCount"
} elseif (-not $isOragornSubagentNoteOnly) {
  $lines += "○───activity─────────────────────"

  if ($mode -eq 'oragorn') {
    $delegated = @($mainEvents | Where-Object { [string]$_.action -eq 'DELEGATION_SENT' }).Count
    $spawned = @($mainEvents | Where-Object { @('SUBAGENT_SPAWN','SUBAGENT_SPAWNED') -contains ([string]$_.action) }).Count
    $completed = @($mainEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FINISH' }).Count
    $failed = @($mainEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FAIL' }).Count
    $totalActions = $delegated + $spawned + $completed + $failed

    $lines += "Delegations: $delegated"
    $lines += "Sub-agents spawned: $spawned"
    $lines += "Sub-agents finished: $completed"
    $lines += "Sub-agents failed: $failed"
  } else {
    $lines += "Data ingested: $ingested"
    $lines += "Backtests completed: $btExecuted"
    $lines += "Promotions: $promoted"
    if ($dirVariants -gt 0) { $lines += "New variants: $dirVariants" }
    if ($forwardRuns -gt 0) { $lines += "Forward checks: $forwardRuns" }
  }
}
# Shared bottom note block (up to 3 lines)
if ($true) {
  $topWarning = $null
  if ($warnings.Count -gt 0) {
    $uniqueWarnings = @{}
    foreach ($w in $warnings) {
      $cur = if ($uniqueWarnings.ContainsKey($w)) { $uniqueWarnings[$w] } else { 0 }
      $uniqueWarnings[$w] = $cur + 1
    }
    $topWarningEntry = @($uniqueWarnings.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1)
    if ($topWarningEntry.Count -gt 0) {
      $tw = $topWarningEntry[0]
      $suffix = if ($tw.Value -gt 1) { " x$($tw.Value)" } else { "" }
      $topWarning = "$($tw.Key)$suffix"
    }
  }

  $noteText = $null

  if ($isOragornSubagentNoteOnly) {
    $finishedCount = @($oragornSubagentCompletionEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FINISH' }).Count
    $failedCount = @($oragornSubagentCompletionEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FAIL' }).Count

    if ($finishedCount -gt 0 -and $failedCount -eq 0) {
      if ($finishedCount -eq 1) {
        $noteText = "A sub-agent just finished successfully and I logged the completion."
      } else {
        $noteText = "$finishedCount sub-agents finished successfully and I logged their completions."
      }
    } elseif ($failedCount -gt 0 -and $finishedCount -eq 0) {
      if ($failedCount -eq 1) {
        $noteText = "A sub-agent run failed and I logged it for follow-up."
      } else {
        $noteText = "$failedCount sub-agent runs failed and I logged them for follow-up."
      }
    } else {
      $noteText = "$finishedCount sub-agents finished and $failedCount failed; all outcomes were logged for follow-up."
    }
  } elseif ($errors -gt 0) {
    $noteText = "I hit $errors issue(s) in this window and need a quick review."
  } elseif ($mode -eq 'frodex' -and ($dirVariants -gt 0 -or $ingested -gt 0 -or $btExecuted -gt 0 -or $promoted -gt 0)) {
    if ($promoted -gt 0) {
      $noteText = "Utility advanced promotion flow this cycle."
    } elseif ($btExecuted -gt 0) {
      $noteText = "Utility completed backtests and recorded results."
    } elseif ($dirVariants -gt 0) {
      $noteText = "Utility generated new variants this cycle."
    } else {
      $noteText = "Utility ingested new inputs and is progressing normally."
    }
  } elseif ($stall -gt 5) {
    if ($forwardRuns -gt 0 -or $forwardSignalEvals -gt 0) {
      $noteText = "Strategy generation is stalled ($stall cycles), but forward-testing is active."
    } else {
      $noteText = "I did not produce new variants for $stall cycles, so exploration is stalled."
    }
  } elseif ($starvation -gt 10) {
    $noteText = "I am input-starved for $starvation cycles, so throughput is constrained."
  } elseif ($topWarning) {
    $noteText = "I flagged a warning to watch: $topWarning"
  } else {
    if ($mode -eq 'oragorn') {
      if ($completed -gt 0 -or $failed -gt 0) {
        $noteText = "Commander lifecycle updated: $completed finished, $failed failed."
      } elseif ($delegated -gt 0) {
        $noteText = "Commander delegated $delegated task(s) this window."
      } else {
        $noteText = "Commander had no new delegation actions in this window."
      }
    } elseif ($mode -eq 'quandalf') {
      if ($strategyResearchCount + $strategyGenerateCount + $doctrineSynthesisCount + $backtestAuditCount -gt 0) {
        $noteText = "Strategist cycle completed and orders/journal are in sync."
      } else {
        $noteText = "No strategist runs were recorded in this window."
      }
    } else {
      if ($promoted -gt 0) {
        $noteText = "Utility advanced promotion flow this cycle."
      } elseif ($btExecuted -gt 0) {
        $noteText = "Utility completed backtests and recorded results."
      } elseif ($forwardRuns -gt 0) {
        $noteText = "Utility forward checks are active and healthy."
      } else {
        $noteText = "Utility cycle was quiet; no actionable changes this window."
      }
    }
  }

  if ($mode -eq 'frodex' -and -not $isOragornSubagentNoteOnly) {
    $recentEvidence = @()
    $tailEvents = @($mainEvents | Where-Object {
      $a = [string]$_.action
      $s = [string]$_.summary
      -not [string]::IsNullOrWhiteSpace($a) -and -not [string]::IsNullOrWhiteSpace($s)
    } | Select-Object -Last 3)

    foreach ($ev in $tailEvents) {
      $a = [string]$ev.action
      $s = ([string]$ev.summary -replace '\s+', ' ').Trim()
      if ($s.Length -gt 90) { $s = $s.Substring(0, 90).TrimEnd() + '…' }
      if (-not [string]::IsNullOrWhiteSpace($s)) {
        $recentEvidence += ($a + ': ' + $s)
      }
    }

    if ($recentEvidence.Count -gt 0) {
      $noteText = 'Cycle evidence: ' + ($recentEvidence -join ' | ')
    }
  }

  $noteText = ($noteText -replace '\s+', ' ').Trim()
  if ($noteText.Length -gt 400) { $noteText = $noteText.Substring(0, 400) }
  if ([string]::IsNullOrWhiteSpace($noteText)) { $noteText = 'All clear this cycle.' }

  $lines += "○───note─────────────────────────"
  $lines += $noteText
}
$messageBody = ($lines -join "`n").TrimEnd()

function Escape-Html {
  param([string]$Text)
  if ($null -eq $Text) { return "" }
  $escaped = [string]$Text
  $escaped = $escaped -replace '&', '&amp;'
  $escaped = $escaped -replace '<', '&lt;'
  $escaped = $escaped -replace '>', '&gt;'
  return $escaped
}

$escapedBody = Escape-Html -Text $messageBody
if ($escapedBody.Length -gt 985) { $escapedBody = $escapedBody.Substring(0, 982) + "..." }
$caption = "<pre>" + $escapedBody + "</pre>"

# --- Send ---
function Send-TextMessage {
  param($tok, $chatId, $text)
  $uri = "https://api.telegram.org/bot$tok/sendMessage"
  $body = @{ chat_id = $chatId; text = ("<pre>" + (Escape-Html -Text $text) + "</pre>"); parse_mode = "HTML" } | ConvertTo-Json -Compress
  Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" | Out-Null
}

if ($bannerPath) {
  $uri = "https://api.telegram.org/bot$telegramSendToken/sendPhoto"
  $boundary = [System.Guid]::NewGuid().ToString()
  $parts = @()
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"chat_id`"`r`n`r`n$logChannel"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"caption`"`r`n`r`n$caption"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"parse_mode`"`r`n`r`nHTML"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"photo`"; filename=`"banner.jpg`"`r`nContent-Type: image/jpeg`r`n"

  $preBytes = [System.Text.Encoding]::UTF8.GetBytes(($parts -join "`r`n") + "`r`n")
  $photoBytes = [System.IO.File]::ReadAllBytes($bannerPath)
  $endBytes = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
  $fullBody = New-Object byte[] ($preBytes.Length + $photoBytes.Length + $endBytes.Length)
  [System.Buffer]::BlockCopy($preBytes, 0, $fullBody, 0, $preBytes.Length)
  [System.Buffer]::BlockCopy($photoBytes, 0, $fullBody, $preBytes.Length, $photoBytes.Length)
  [System.Buffer]::BlockCopy($endBytes, 0, $fullBody, ($preBytes.Length + $photoBytes.Length), $endBytes.Length)

  try {
    Invoke-RestMethod -Uri $uri -Method Post -Body $fullBody -ContentType "multipart/form-data; boundary=$boundary" | Out-Null
    Write-Host "Bundle sent to log channel with banner"
  } catch {
    Write-Host "Photo failed: $_"
    Write-Host "Skipped text fallback (images-only mode)"
  }
} else {
  Write-Host "No banner available; skipped send (images-only mode)"
}

$messageBody | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
Write-Host "Done"

