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
$nowUtc = (Get-Date).ToUniversalTime()
$windowStartUtc = $nowUtc.AddMinutes(-1 * $effectiveWindow)
$windowEndUtc = $nowUtc

# For frodex 15m cadence, anchor window to quarter-hour slots so delayed sends
# still report the intended cycle (e.g., 12:15 report = 12:00-12:15 activity).
if ($mode -eq 'frodex') {
  $slotMinutes = 15
  $anchorUtc = [DateTime]::new($nowUtc.Year, $nowUtc.Month, $nowUtc.Day, $nowUtc.Hour, $nowUtc.Minute, 0, [DateTimeKind]::Utc)
  $minuteRemainder = $anchorUtc.Minute % $slotMinutes
  $windowEndUtc = $anchorUtc.AddMinutes(-1 * $minuteRemainder)
  if ($windowEndUtc -gt $nowUtc) {
    $windowEndUtc = $windowEndUtc.AddMinutes(-1 * $slotMinutes)
  }
  $windowStartUtc = $windowEndUtc.AddMinutes(-1 * $slotMinutes)
}

$tailLines = switch ($mode) {
  'oragorn' { 5000 }
  'quandalf' { 1500 }
  default { 1200 }
}
$events = @()
$allTailEvents = @()
foreach ($line in (Get-Content $logPath -Encoding UTF8 -Tail $tailLines)) {
  try {
    $entry = $line | ConvertFrom-Json
    $tsRaw = if ($entry.ts_iso) { $entry.ts_iso } elseif ($entry.ts) { $entry.ts } else { $null }
    if (-not $tsRaw) { continue }
    try { $ts = [DateTime]::Parse($tsRaw).ToUniversalTime() } catch { continue }

    try { $entry | Add-Member -NotePropertyName '__ts_utc' -NotePropertyValue $ts -Force } catch {}
    $allTailEvents += $entry

    if ($ts -ge $windowStartUtc -and $ts -lt $windowEndUtc) { $events += $entry }
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

function Get-RunGroupKey {
  param([string]$RunId, [string]$Mode)
  if ([string]::IsNullOrWhiteSpace($RunId)) { return $null }
  if ($Mode -eq 'frodex') {
    if ($RunId -match '^(autopilot-\d+)') { return $matches[1] }
    return $null
  }
  return $RunId
}

$durationLabel = '<1s'
$selectedRunKey = $null

$runSourceEvents = if ($mode -eq 'frodex') { $allTailEvents } else { $mainEvents }
$mainWithRun = @($runSourceEvents | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.run_id) })
if ($mainWithRun.Count -gt 0) {
  $groupRows = @()
  foreach ($ev in $mainWithRun) {
    $rid = [string]$ev.run_id
    $key = Get-RunGroupKey -RunId $rid -Mode $mode
    if ([string]::IsNullOrWhiteSpace($key)) { continue }
    $ts = $null
    if ($ev.PSObject.Properties.Name -contains '__ts_utc') { $ts = $ev.__ts_utc }
    if ($null -eq $ts) { $ts = Get-EventUtcTimestamp $ev }
    if ($null -eq $ts) { continue }
    $groupRows += [PSCustomObject]@{ key = $key; ts = $ts }
  }

  if ($groupRows.Count -gt 0) {
    $grouped = @($groupRows | Group-Object key)
    $latest = $null
    $latestTs = $null

    if ($mode -eq 'frodex') {
      $terminalActions = @('LAB_SUMMARY','AUTOPILOT_EXCEPTION')
      $terminalCandidates = @()
      foreach ($ev in $allTailEvents) {
        $rid = [string]$ev.run_id
        $key = Get-RunGroupKey -RunId $rid -Mode $mode
        if ([string]::IsNullOrWhiteSpace($key)) { continue }
        $act = [string]$ev.action
        if (-not ($terminalActions -contains $act)) { continue }
        $ts = $null
        if ($ev.PSObject.Properties.Name -contains '__ts_utc') { $ts = $ev.__ts_utc }
        if ($null -eq $ts) { $ts = Get-EventUtcTimestamp $ev }
        if ($null -eq $ts) { continue }
        $terminalCandidates += [PSCustomObject]@{ key = $key; ts = $ts }
      }
      if ($terminalCandidates.Count -gt 0) {
        $latestTerminal = @($terminalCandidates | Sort-Object ts | Select-Object -Last 1)
        if ($latestTerminal.Count -gt 0) {
          $selectedRunKey = [string]$latestTerminal[0].key
        }
      }
    }

    if ([string]::IsNullOrWhiteSpace($selectedRunKey)) {
      foreach ($g in $grouped) {
        $endTs = @($g.Group | ForEach-Object { $_.ts } | Sort-Object)[-1]
        if ($null -eq $latestTs -or $endTs -gt $latestTs) {
          $latestTs = $endTs
          $latest = $g.Name
        }
      }
      $selectedRunKey = $latest
    }
  }
}

if (-not [string]::IsNullOrWhiteSpace($selectedRunKey)) {
  $runTs = @()
  $handoffTs = @()
  foreach ($ev in $allTailEvents) {
    $rid = [string]$ev.run_id
    $key = Get-RunGroupKey -RunId $rid -Mode $mode
    if ($key -ne $selectedRunKey) { continue }
    $ts = $null
    if ($ev.PSObject.Properties.Name -contains '__ts_utc') { $ts = $ev.__ts_utc }
    if ($null -eq $ts) { $ts = Get-EventUtcTimestamp $ev }
    if ($null -eq $ts) { continue }

    $runTs += $ts
    if ($mode -eq 'frodex' -and [string]$ev.action -eq 'DECISION_HANDOFF') {
      $handoffTs += $ts
    }
  }

  $runTs = @($runTs | Sort-Object)
  $handoffTs = @($handoffTs | Sort-Object)

  if ($runTs.Count -ge 2) {
    $startTs = $runTs[0]
    $endTs = $runTs[-1]
    if ($mode -eq 'frodex' -and $handoffTs.Count -gt 0) {
      # Frodex duration contract: cycle start -> first handoff emitted.
      $endTs = $handoffTs[0]
    }

    $runDuration = ($endTs - $startTs)
    if ($runDuration.TotalSeconds -gt 0) {
      $durationLabel = Format-CompactDuration $runDuration
    }
  }
}

if ($durationLabel -eq '<1s') {
  $eventTimestamps = @($mainEvents | ForEach-Object { Get-EventUtcTimestamp $_ } | Where-Object { $_ -ne $null } | Sort-Object)
  if ($eventTimestamps.Count -ge 2) {
    $windowDuration = ($eventTimestamps[-1] - $eventTimestamps[0])
    if ($windowDuration.TotalSeconds -gt 0) {
      $durationLabel = Format-CompactDuration $windowDuration
    }
  }
}

$reportEvents = $mainEvents
if ($mode -eq 'frodex' -and -not [string]::IsNullOrWhiteSpace($selectedRunKey)) {
  $reportEvents = @(
    $allTailEvents |
    Where-Object {
      $rid = [string]$_.run_id
      if ([string]::IsNullOrWhiteSpace($rid)) { return $false }
      (Get-RunGroupKey -RunId $rid -Mode $mode) -eq $selectedRunKey
    }
  )
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
$grabbed = 0; $grabFailed = 0; $grabSkipped = 0; $videosGrabbed = 0; $videoFailed = 0; $videoSkipped = 0
$btRuns = 0; $btExecuted = 0; $btSkipped = 0
$promoted = 0
$refined = 0
$librarySize = 0; $libNew = 0; $libLessons = 0
$dirNotes = 0; $dirVariants = 0; $dirExplore = 0
$ingested = 0; $errors = 0; $passingGate = 0; $generated = 0; $queuedBacklog = 0
$insightNew = 0
$stall = 0; $starvation = 0
$warnings = @()
$errorHighlights = @()
$forwardRuns = 0; $forwardEntries = 0; $forwardCloses = 0; $forwardSignalEvals = 0; $forwardOpenPositions = 0
$delegated = 0; $spawned = 0; $completed = 0; $failed = 0; $totalActions = 0
$bundlesScanned = 0; $bundlesSelected = 0; $bundleStarts = 0
$specOk = 0; $specBlocked = 0; $specReview = 0
$batchAttempts = 0; $batchExecutedTotal = 0; $batchSkippedTotal = 0; $batchBlockedPromotion = 0; $batchNoVariants = 0
$promotionChecks = 0; $promotionOk = 0; $promotionBlocked = 0; $promotionSkipped = 0
$outboxLag = 0

foreach ($e in $reportEvents) {
  $sum = if ($e.summary) { $e.summary } else { "" }
  $act = if ($e.action) { $e.action } else { "" }
  $stat = if ($e.status_word) { $e.status_word.ToUpper() } else { "OK" }

  switch ($act) {
    "GRABBER_SUMMARY" {
      if ($sum -match 'fetched=(\d+)') { $grabbed = [int]$matches[1] }
      if ($sum -match 'failed=(\d+)') { $grabFailed = [int]$matches[1] }
      if ($sum -match 'dedup=(\d+)') { $grabSkipped += [int]$matches[1] }
      if ($sum -match 'too_large_skipped_count=(\d+)') { $grabSkipped += [int]$matches[1] }
    }
    "YT_WATCH_SUMMARY" {
      if ($sum -match 'new=(\d+)') { $videosGrabbed = [int]$matches[1] }
      elseif ($sum -match 'processed=(\d+)') { $videosGrabbed = [int]$matches[1] }
      if ($sum -match 'failed=(\d+)') { $videoFailed = [int]$matches[1] }
      if ($sum -match 'dedup=(\d+)') { $videoSkipped = [int]$matches[1] }
    }
    "BUNDLE_SCAN_DIAG" {
      if ($sum -match 'new=(\d+)') { $bundlesScanned = [int]$matches[1] }
      elseif ($sum -match 'total=(\d+)') { $bundlesScanned = [int]$matches[1] }
    }
    "BUNDLE_SELECT_DIAG" {
      if ($sum -match 'selected=(\d+)') { $bundlesSelected = [int]$matches[1] }
      elseif ($sum -match 'processable=(\d+)') { $bundlesSelected = [int]$matches[1] }
      elseif ($sum -match 'new_count=(\d+)') { $bundlesSelected = [int]$matches[1] }
    }
    "BUNDLE_PROCESS_START" {
      $bundleStarts++
    }
    "BUNDLE_SPEC_RESULT" {
      if ($sum -match 'spec_status=([A-Z_]+)') {
        $sst = [string]$matches[1]
        if ($sst -eq 'OK') { $specOk++ }
        elseif ($sst -eq 'BLOCKED') { $specBlocked++ }
        elseif ($sst -eq 'REVIEW_REQUIRED') { $specReview++ }
      }
    }
    "BATCH_BACKTEST_SUMMARY" {
      $batchAttempts++
      if ($sum -match 'runs=(\d+)') { $btRuns = [int]$matches[1] }
      if ($sum -match 'executed=(\d+)') {
        $btExecuted = [int]$matches[1]
        $batchExecutedTotal += [int]$matches[1]
      }
      if ($sum -match 'skipped=(\d+)') {
        $btSkipped = [int]$matches[1]
        $batchSkippedTotal += [int]$matches[1]
      }
      if ($sum -match 'blocked promotion') { $batchBlockedPromotion++ }
      if ($sum -match 'no variants') { $batchNoVariants++ }
    }
    "LIBRARIAN_SUMMARY" {
      if ($sum -match 'run=(\d+)') { $librarySize = [int]$matches[1] }
      if ($sum -match 'new=(\d+)') { $libNew = [int]$matches[1] }
      if ($sum -match 'lessons=(\d+)') { $libLessons = [int]$matches[1] }
    }
    "PROMOTION_SUMMARY" {
      $promotionChecks++
      if ($sum -match 'variants=(\d+)') { $promoted = [int]$matches[1] }
      if ($sum -match 'status=([A-Z_]+)') {
        $pstat = [string]$matches[1]
        if ($pstat -eq 'OK') { $promotionOk++ }
        elseif ($pstat -eq 'BLOCKED' -or $pstat -eq 'REVIEW_REQUIRED') { $promotionBlocked++ }
        elseif ($pstat -eq 'SKIPPED') { $promotionSkipped++ }
      }
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
    "LAB_THROUGHPUT_DROUGHT_WARN" {
      if ($sum -match 'throughput_drought_cycles[=:\s]+(\d+)') { $starvation = [int]$matches[1] }
      elseif ($sum -match '(\d+)') { $starvation = [int]$matches[1] }
    }
    "LAB_SUMMARY" {
      if ($sum -match 'ingested=(\d+)') { $ingested = [int]$matches[1] }
      if ($sum -match 'passing_gate=(\d+)') { $passingGate = [int]$matches[1] }
      if ($sum -match 'generated=(\d+)') { $generated = [int]$matches[1] }
      if ($sum -match 'queued_for_testing=(\d+)') { $queuedBacklog = [int]$matches[1] }
      elseif ($sum -match 'backlog=(\d+)') { $queuedBacklog = [int]$matches[1] }
      if ($sum -match 'errors=(\d+)') { $errors = [int]$matches[1] }
      if ($sum -match 'throughput_drought_cycles[=:\s]+(\d+)') { $starvation = [int]$matches[1] }
      elseif ($sum -match 'starvation[=:\s]+(\d+)') { $starvation = [int]$matches[1] }
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
    if ($reasonCode -notmatch "STALL|STARVATION|THROUGHPUT_DROUGHT") { $warnings += $wKey }

    if ($stat -in @('FAIL','BLOCKED')) {
      $detail = switch ($reasonCode) {
        'AUTOPILOT_EXCEPTION' {
          if ($sum -match '(?i)stream was not readable') { 'a temporary stream-read glitch interrupted one step' }
          elseif ($sum -match '(?i)lock') { 'another run was active, so this attempt could not take the lock' }
          else { 'the autopilot worker hit an exception' }
        }
        'BRAIN_VALIDATE_FAIL' { 'brain validation blocked execution because required evidence pointers were not valid' }
        'REPO_HYGIENE_GATE' { 'repo hygiene gate blocked the cycle due to a policy violation' }
        'LAB_SUMMARY' { 'the cycle summary recorded a blocking issue in this window' }
        default {
          $txt = ($reasonCode -replace '_', ' ').ToLowerInvariant()
          if ([string]::IsNullOrWhiteSpace($txt)) { 'a blocking issue occurred' } else { $txt }
        }
      }
      $errorHighlights += ($agentName + ': ' + $detail)
    }
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
        if ($fts -lt $windowStartUtc -or $fts -ge $windowEndUtc) { continue }

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

if ($mode -eq 'frodex') {
  $outboxPath = "$ROOT\data\logs\outbox"
  if (Test-Path $outboxPath) {
    try { $outboxLag = @((Get-ChildItem -Path $outboxPath -File -ErrorAction SilentlyContinue)).Count } catch { $outboxLag = 0 }
  }
}

# --- Build message ---
$hasErrors = $errors -gt 0
$hasWarnings = ($stall -gt 5) -or ($starvation -gt 10) -or ($warnings.Count -gt 0)
$statusTag = if ($hasErrors) { "FAIL" } elseif ($hasWarnings) { "WARN" } else { "OK" }

# Do not paint the card red for transient issues when the same window shows successful work.
if ($mode -eq 'frodex' -and $statusTag -eq 'FAIL') {
  $recoverySignals = ($batchExecutedTotal -gt 0) -or ($specOk -gt 0) -or ($promotionOk -gt 0) -or (@($reportEvents | Where-Object { [string]$_.action -eq 'DECISION_HANDOFF' }).Count -gt 0)
  if ($recoverySignals -and $errors -le 1) {
    $statusTag = 'WARN'
  }
}

$iconOk = [char]0x2705
$iconWarn = ([char]0x26A0) + ([char]0xFE0F)
$iconFail = [char]0x274C
$statusIcon = switch ($statusTag) {
  "OK" { $iconOk }
  "WARN" { $iconWarn }
  "FAIL" { $iconFail }
}

$emojiAlgo = [System.Char]::ConvertFromUtf32(0x1F4CA)
$emojiReflect = [System.Char]::ConvertFromUtf32(0x1FA9E)
$emojiCommander = [System.Char]::ConvertFromUtf32(0x1F451)
$titleLine = switch ($mode) {
  'quandalf' { $emojiReflect + ' Reflecting' }
  'oragorn' { $emojiCommander + ' Commander Actions' }
  default { '🍳 Cooking' }
}

$lines = @()
$lines += $titleLine
$lines += ("Status: " + $statusIcon + " | Duration: " + $durationLabel)

$strategyGenerateCount = @($reportEvents | Where-Object { [string]$_.action -eq 'strategy_generate' }).Count
$strategyResearchCount = @($reportEvents | Where-Object { [string]$_.action -eq 'strategy_research' }).Count
$doctrineSynthesisCount = @($reportEvents | Where-Object { [string]$_.action -eq 'doctrine_synthesis' }).Count
$backtestAuditCount = @($reportEvents | Where-Object { [string]$_.action -eq 'backtest_audit' }).Count
$totalStrictRuns = $strategyGenerateCount + $strategyResearchCount + $doctrineSynthesisCount + $backtestAuditCount

if ($mode -eq 'quandalf') {
  $reviewedCount = $strategyResearchCount + $backtestAuditCount
  $advancedCount = $strategyGenerateCount
  $passedCount = 0
  $abortedCount = $errors
  $generatedCount = $strategyGenerateCount
  $queuedCount = $strategyGenerateCount

  $lines += "○───activity─────────────────────"
  $lines += "Reviewed: $reviewedCount"
  $lines += "Promoted: $advancedCount"
  $lines += "Passed: $passedCount"
  $lines += "Aborted: $abortedCount"
  $lines += "Generated: $generatedCount"
  $lines += "Queued: $queuedCount"
} elseif (-not $isOragornSubagentNoteOnly) {
  $lines += "○───activity─────────────────────"

  if ($mode -eq 'oragorn') {
    $delegated = @($reportEvents | Where-Object { [string]$_.action -eq 'DELEGATION_SENT' }).Count
    $spawned = @($reportEvents | Where-Object { @('SUBAGENT_SPAWN','SUBAGENT_SPAWNED') -contains ([string]$_.action) }).Count
    $completed = @($reportEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FINISH' }).Count
    $failed = @($reportEvents | Where-Object { [string]$_.action -eq 'SUBAGENT_FAIL' }).Count
    $totalActions = $delegated + $spawned + $completed + $failed

    $lines += "Delegations: $delegated"
    $lines += "Sub-agents spawned: $spawned"
    $lines += "Sub-agents finished: $completed"
    $lines += "Sub-agents failed: $failed"
  } else {
    $lines += "Waiting: $outboxLag"
    $lines += "Backtests: $batchExecutedTotal"
    $lines += "Requeued: $batchSkippedTotal"
    $lines += "Aborted: $batchGateFail"
    $lines += "Forwardtests: $forwardRuns"
  }
}
# Shared bottom note block (up to 3 lines)
if ($true) {
  $topWarning = $null
  $topWarningCount = 0
  if ($warnings.Count -gt 0) {
    $uniqueWarnings = @{}
    foreach ($w in $warnings) {
      $cur = if ($uniqueWarnings.ContainsKey($w)) { $uniqueWarnings[$w] } else { 0 }
      $uniqueWarnings[$w] = $cur + 1
    }
    $topWarningEntry = @($uniqueWarnings.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1)
    if ($topWarningEntry.Count -gt 0) {
      $tw = $topWarningEntry[0]
      $topWarningCount = [int]$tw.Value
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
    if ($errorHighlights.Count -gt 0) {
      $primaryErr = [string]$errorHighlights[0]
      $noteText = "I hit $errors issue(s); the main one was $primaryErr."
    } else {
      $noteText = "I hit $errors issue(s) in this window and need a quick review."
    }
  } elseif ($mode -eq 'frodex') {
    if ($errors -gt 0) {
      $noteText = "Issues detected this cycle; I flagged them for follow-up."
    } elseif ($promotionOk -gt 0 -and $promotionBlocked -gt 0) {
      $noteText = "Strong cycle: $promotionOk promoted, $promotionBlocked held for review."
    } elseif ($promotionOk -gt 0) {
      $noteText = "Strong cycle: $promotionOk promoted cleanly."
    } elseif ($batchSkippedTotal -gt 0) {
      $noteText = "Cycle complete with skips: $batchSkippedTotal item(s) were returned for rectify/abort."
    } elseif ($batchExecutedTotal -gt 0) {
      $noteText = "Cycle complete: $batchExecutedTotal backtests run; no strong promotion yet."
    } elseif ($ingested -gt 0 -or $bundlesSelected -gt 0 -or ($specOk + $specBlocked + $specReview) -gt 0) {
      $noteText = "Pipeline moved through ingest and validation this window."
    } elseif ($forwardRuns -gt 0) {
      $noteText = "Forward testing stayed active while the lab window was quiet."
    } else {
      $noteText = "Quiet cycle; no actionable changes in this window."
    }
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

  $statusSentence = switch ($statusTag) {
    "OK" { "System status is healthy this cycle." }
    "WARN" { "System status needs attention this cycle." }
    "FAIL" { "System status is blocked this cycle." }
    default { "System status is unknown this cycle." }
  }

  if ([string]::IsNullOrWhiteSpace($noteText)) {
    $noteText = $statusSentence
  } else {
    $noteText = "$statusSentence $noteText"
  }

  $noteText = ($noteText -replace '\s+', ' ').Trim()
  if ($noteText.Length -gt 365) { $noteText = $noteText.Substring(0, 365) }
  if ([string]::IsNullOrWhiteSpace($noteText)) { $noteText = 'All clear this cycle.' }

  $lines += "○───note─────────────────────────"
  $lines += $noteText
}
$messageBody = ($lines -join "`n").TrimEnd()

$intakeBody = $null
if ($mode -eq 'frodex') {
  $intakeSkipped = [int]$grabSkipped + [int]$videoSkipped
  $intakeFailed = [int]$grabFailed + [int]$videoFailed
  $intakeLines = @()
  $intakeLines += '⚡ Intake'
  $intakeLines += ('Status: ' + $statusIcon + ' | Duration: ' + $durationLabel)
  $intakeLines += '○───intake─────────────────'
  $intakeLines += ('Videos: ' + [int]$videosGrabbed)
  $intakeLines += ('Indicators: ' + [int]$grabbed)
  $intakeLines += ('Skipped: ' + [int]$intakeSkipped)
  $intakeLines += ('Failed: ' + [int]$intakeFailed)
  $intakeBody = ($intakeLines -join "`n").TrimEnd()
}

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

$intakeCaption = $null
if (-not [string]::IsNullOrWhiteSpace($intakeBody)) {
  $escapedIntake = Escape-Html -Text $intakeBody
  if ($escapedIntake.Length -gt 985) { $escapedIntake = $escapedIntake.Substring(0, 982) + "..." }
  $intakeCaption = "<pre>" + $escapedIntake + "</pre>"
}

if ($mode -eq 'frodex' -and [string]::IsNullOrWhiteSpace($selectedRunKey)) {
  Write-Host "No completed Frodex run found; skipping bundle send"
  $messageBody | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
  Write-Host "Done"
  exit 0
}

# --- Duplicate guard (same payload in short window) ---
$reportStatePath = "$ROOT\data\state\bundle_report_state.json"
$reportState = @{}
try {
  if (Test-Path -LiteralPath $reportStatePath) {
    $loaded = Get-Content -LiteralPath $reportStatePath -Raw | ConvertFrom-Json
    if ($loaded) {
      foreach ($prop in $loaded.PSObject.Properties) {
        $reportState[[string]$prop.Name] = $prop.Value
      }
    }
  }
} catch { $reportState = @{} }

$hashInput = [System.Text.Encoding]::UTF8.GetBytes(($mode + "|" + $messageBody))
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
  $hashHex = ([BitConverter]::ToString($sha.ComputeHash($hashInput))).Replace('-', '').ToLowerInvariant()
} finally {
  $sha.Dispose()
}

$stateKey = ($mode + "_last")
$minSendIntervalSeconds = 720
$minRepeatSeconds = 1800
$skipDuplicateSend = $false
try {
  $node = $reportState.$stateKey
  if ($node) {
    $prevHash = [string]$node.hash
    $prevAt = [string]$node.sent_at
    $prevRunId = [string]$node.last_run_id

    if ($mode -eq 'frodex' -and -not [string]::IsNullOrWhiteSpace($selectedRunKey) -and $prevRunId -eq $selectedRunKey) {
      $skipDuplicateSend = $true
    }

    $isRunDrivenFrodex = ($mode -eq 'frodex' -and -not [string]::IsNullOrWhiteSpace($selectedRunKey))
    if (-not $skipDuplicateSend -and -not $isRunDrivenFrodex -and -not [string]::IsNullOrWhiteSpace($prevAt)) {
      $prevDt = [DateTime]::Parse($prevAt).ToUniversalTime()
      $ageSec = ([DateTime]::UtcNow - $prevDt).TotalSeconds
      if ($ageSec -lt $minSendIntervalSeconds) {
        $skipDuplicateSend = $true
      } elseif (-not [string]::IsNullOrWhiteSpace($prevHash) -and $prevHash -eq $hashHex -and $ageSec -lt $minRepeatSeconds) {
        $skipDuplicateSend = $true
      }
    }
  }
} catch {}

# --- Send ---
function Send-TextMessage {
  param($tok, $chatId, $text)
  $uri = "https://api.telegram.org/bot$tok/sendMessage"
  $body = @{ chat_id = $chatId; text = ("<pre>" + (Escape-Html -Text $text) + "</pre>"); parse_mode = "HTML" } | ConvertTo-Json -Compress
  Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" | Out-Null
}

if ($skipDuplicateSend) {
  Write-Host "Skipped duplicate bundle send (within min interval or repeated payload)"
} else {
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
      $reportState[$stateKey] = @{ hash = $hashHex; sent_at = [DateTime]::UtcNow.ToString('o'); last_run_id = $selectedRunKey }
      ($reportState | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $reportStatePath -Encoding utf8
      Write-Host "Bundle sent to log channel with banner"
      if ($mode -eq 'frodex' -and -not [string]::IsNullOrWhiteSpace($intakeCaption)) {
        try {
          $boundary2 = [System.Guid]::NewGuid().ToString()
          $parts2 = @()
          $parts2 += "--$boundary2`r`nContent-Disposition: form-data; name=`"chat_id`"`r`n`r`n$logChannel"
          $parts2 += "--$boundary2`r`nContent-Disposition: form-data; name=`"caption`"`r`n`r`n$intakeCaption"
          $parts2 += "--$boundary2`r`nContent-Disposition: form-data; name=`"parse_mode`"`r`n`r`nHTML"
          $parts2 += "--$boundary2`r`nContent-Disposition: form-data; name=`"photo`"; filename=`"banner.jpg`"`r`nContent-Type: image/jpeg`r`n"
          $preBytes2 = [System.Text.Encoding]::UTF8.GetBytes(($parts2 -join "`r`n") + "`r`n")
          $fullBody2 = New-Object byte[] ($preBytes2.Length + $photoBytes.Length + $endBytes.Length)
          [System.Buffer]::BlockCopy($preBytes2, 0, $fullBody2, 0, $preBytes2.Length)
          [System.Buffer]::BlockCopy($photoBytes, 0, $fullBody2, $preBytes2.Length, $photoBytes.Length)
          [System.Buffer]::BlockCopy($endBytes, 0, $fullBody2, ($preBytes2.Length + $photoBytes.Length), $endBytes.Length)
          Invoke-RestMethod -Uri $uri -Method Post -Body $fullBody2 -ContentType "multipart/form-data; boundary=$boundary2" | Out-Null
          Write-Host "Speedster intake card sent with banner"
        } catch {
          Write-Host "Intake photo failed: $_"
        }
      }
    } catch {
      Write-Host "Photo failed: $_"
      Write-Host "Skipped text fallback (images-only mode)"
    }
  } else {
    Write-Host "No banner available; skipped send (images-only mode)"
  }
}

$messageBody | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
Write-Host "Done"






