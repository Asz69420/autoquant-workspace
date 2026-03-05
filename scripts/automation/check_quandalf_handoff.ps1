param(
  [string]$RunIdHint = ''
)

$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location -LiteralPath $ROOT

$actionsPath = Join-Path $ROOT 'data\logs\actions.ndjson'
$statePath = Join-Path $ROOT 'data\state\quandalf_handoff_poll_state.json'
$lockDir = Join-Path $ROOT 'data\state\locks\quandalf_handoff_poll.lockdir'
$jobId = 'b6d07171-ab62-4038-a4ec-4a5ac7b3d0d7'
$ordersPath = Join-Path $ROOT 'docs\shared\QUANDALF_ORDERS.md'
$resultsPath = Join-Path $ROOT 'docs\shared\LAST_CYCLE_RESULTS.md'
$autopilotSummaryPath = Join-Path $ROOT 'data\state\autopilot_summary.json'
$quandalfReflectionStatePath = Join-Path $ROOT 'data\state\quandalf_reflection_state.json'
$autopilotWorkerLockPath = Join-Path $ROOT 'data\state\locks\autopilot_worker.lock'
$runtimeFlagsPath = Join-Path $ROOT 'config\runtime_flags.json'

# Handoff guard timing: ensure upstream run is settled, then apply cooldown.
$settleQuietSeconds = 4
$handoffBufferSeconds = 10
$settleTimeoutSeconds = 180

function Escape-Html {
  param([string]$Text)
  if ($null -eq $Text) { return '' }
  $escaped = [string]$Text
  $escaped = $escaped -replace '&', '&amp;'
  $escaped = $escaped -replace '<', '&lt;'
  $escaped = $escaped -replace '>', '&gt;'
  return $escaped
}

function Get-TelegramLogConfig {
  $wsEnv = Join-Path $ROOT '.env'
  if (-not (Test-Path -LiteralPath $wsEnv)) { return $null }

  $token = $null
  $logBotToken = $null
  $logChannel = $null
  Get-Content -LiteralPath $wsEnv -Encoding UTF8 | ForEach-Object {
    if ($_ -match '^TELEGRAM_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
    if ($_ -match '^TELEGRAM_LOG_BOT_TOKEN=(.*)$') { $logBotToken = $matches[1].Trim() }
    if ($_ -match '^TELEGRAM_LOG_CHAT_ID=(.*)$') { $logChannel = $matches[1].Trim() }
  }

  if ([string]::IsNullOrWhiteSpace($logChannel)) { return $null }
  $sendToken = if (-not [string]::IsNullOrWhiteSpace($logBotToken)) { $logBotToken } else { $token }
  if ([string]::IsNullOrWhiteSpace($sendToken)) { return $null }

  return [PSCustomObject]@{ token = $sendToken; chat_id = $logChannel }
}

function Get-QuandalfBannerPath {
  $bannerDir = Join-Path $ROOT 'assets\banners'
  if (-not (Test-Path -LiteralPath $bannerDir)) { return $null }
  $file = Get-ChildItem -LiteralPath $bannerDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^quandalf_banner\.' } | Select-Object -First 1
  if ($null -eq $file) { return $null }
  return [string]$file.FullName
}

function Get-CurrentOrderInfo {
  $status = 'unknown'
  $queued = 0
  if (-not (Test-Path -LiteralPath $ordersPath)) {
    return [PSCustomObject]@{ status = $status; queued = $queued }
  }

  $text = Get-Content -LiteralPath $ordersPath -Raw -Encoding UTF8
  $m = [regex]::Match($text, '(?im)^\*\*Status:\*\*\s*([A-Z_]+)')
  if ($m.Success) { $status = $m.Groups[1].Value.ToUpperInvariant() }

  if ($status -eq 'NEW' -or $status -eq 'PENDING') {
    $split = $text -split '(?im)^##\s+Archived Strategy Order', 2
    $active = $split[0]
    $blocks = [regex]::Matches($active, '(?im)^###\s+Strategy\b')
    $queued = $blocks.Count
  }

  return [PSCustomObject]@{ status = $status; queued = $queued }
}

function Get-ResultsReviewInfo {
  $reviewed = 0
  $advanced = 0
  $aborted = 0

  if (-not (Test-Path -LiteralPath $resultsPath)) {
    return [PSCustomObject]@{ reviewed = $reviewed; advanced = $advanced; passed = $advanced; aborted = $aborted; q_generated = 0; q_queued = 0; q_skipped = 0; is_live = $false }
  }

  $lines = Get-Content -LiteralPath $resultsPath -Encoding UTF8
  foreach ($ln in $lines) {
    $line = [string]$ln
    if ($line -notmatch '^\|') { continue }
    if ($line -match '^\|---') { continue }
    if ($line -match '^\|\s*Strategy\s*\|') { continue }

    $reviewed++
    if ($line -match '\|\s*PASS\s*\|') { $advanced++ }
    elseif ($line -match '\|\s*FAIL') { $aborted++ }
  }

  return [PSCustomObject]@{ reviewed = $reviewed; advanced = $advanced; passed = $advanced; aborted = $aborted; q_generated = 0; q_queued = 0; q_skipped = 0; is_live = $false }
}

function Get-RunScopedActions {
  param([string]$RunId)
  $items = @()
  if ([string]::IsNullOrWhiteSpace($RunId)) { return $items }
  if (-not (Test-Path -LiteralPath $actionsPath)) { return $items }
  try {
    $rows = Get-Content -LiteralPath $actionsPath -Tail 4000 -Encoding UTF8
    foreach ($line in $rows) {
      try { $e = $line | ConvertFrom-Json } catch { continue }
      $rid = [string]$e.run_id
      if ($rid.StartsWith($RunId + '-')) { $items += $e }
    }
  } catch {}
  return $items
}

function Get-RunSummaryMetricTotal {
  param(
    [array]$Events,
    [string]$Action,
    [string]$MetricName
  )
  $total = 0
  foreach ($e in @($Events)) {
    if ([string]$e.action -ne $Action) { continue }
    $summary = [string]$e.summary
    $m = [regex]::Match($summary, ('(?i)' + [regex]::Escape($MetricName) + '=(\d+)'))
    if ($m.Success) {
      try { $total += [int]$m.Groups[1].Value } catch {}
    }
  }
  return [int]$total
}

function Get-RunHandoffTimestampUtc {
  param([string]$RunId)
  if ([string]::IsNullOrWhiteSpace($RunId)) { return $null }
  if (-not (Test-Path -LiteralPath $actionsPath)) { return $null }

  $hits = @()
  try {
    $rows = Get-Content -LiteralPath $actionsPath -Tail 4000 -Encoding UTF8
    foreach ($line in $rows) {
      try { $e = $line | ConvertFrom-Json } catch { continue }
      if ([string]$e.action -ne 'DECISION_HANDOFF') { continue }
      $rid = [string]$e.run_id
      if (-not $rid.StartsWith($RunId + '-')) { continue }
      $tsRaw = [string]$e.ts_iso
      if ([string]::IsNullOrWhiteSpace($tsRaw)) { continue }
      try {
        $hits += [DateTime]::Parse($tsRaw).ToUniversalTime()
      } catch {}
    }
  } catch {}

  if (@($hits).Count -eq 0) { return $null }
  return (@($hits | Sort-Object) | Select-Object -First 1)
}

function Get-ReflectionStatusForRun {
  param([string]$RunId)
  if ([string]::IsNullOrWhiteSpace($RunId)) { return $null }
  if (-not (Test-Path -LiteralPath $quandalfReflectionStatePath)) { return $null }
  try {
    $st = Get-Content -LiteralPath $quandalfReflectionStatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $st) { return $null }
    if ([string]$st.last_run_id -ne $RunId) { return $null }
    return [PSCustomObject]@{
      status = [string]$st.last_reflection_status
      note = [string]$st.last_note
      claude_rc = [int]$st.last_claude_rc
    }
  } catch {
    return $null
  }
}

function Get-LiveReviewInfo {
  param([string]$RunId = '')
  if (-not (Test-Path -LiteralPath $autopilotSummaryPath)) {
    return $null
  }

  try {
    $s = Get-Content -LiteralPath $autopilotSummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $s) { return $null }

    $ingested = [int]($s.candidates_ingested)
    $advanced = 0
    try { if ($null -ne $s.candidates_reaching_refinement) { $advanced = [int]$s.candidates_reaching_refinement } } catch {}
    $passing = [int]($s.candidates_passing_gate)
    $errors = [int]($s.errors_count)

    $qGenerated = 0
    $qQueued = 0
    $qSkipped = 0
    try { if ($null -ne $s.quandalf_queue_generated) { $qGenerated = [int]$s.quandalf_queue_generated } } catch {}
    try {
      if ($null -ne $s.queued_for_testing) { $qQueued = [int]$s.queued_for_testing }
      elseif ($null -ne $s.queue_backlog) { $qQueued = [int]$s.queue_backlog }
      elseif ($null -ne $s.frodex_queue_backlog) { $qQueued = [int]$s.frodex_queue_backlog }
      elseif ($null -ne $s.quandalf_queue_ready) { $qQueued = [int]$s.quandalf_queue_ready }
    } catch {}

    # Prefer run-scoped metrics for card correctness (new-cycle values, not aggregate drift).
    if (-not [string]::IsNullOrWhiteSpace($RunId)) {
      $runEvents = Get-RunScopedActions -RunId $RunId
      if (@($runEvents).Count -gt 0) {
        $runGenerated = @($runEvents | Where-Object { [string]$_.action -eq 'BUNDLE_SPEC_RESULT' }).Count
        $runPassed = Get-RunSummaryMetricTotal -Events $runEvents -Action 'BATCH_BACKTEST_SUMMARY' -MetricName 'gate_pass'
        $runAborted = Get-RunSummaryMetricTotal -Events $runEvents -Action 'BATCH_BACKTEST_SUMMARY' -MetricName 'gate_fail'
        $runSkipped = Get-RunSummaryMetricTotal -Events $runEvents -Action 'REQUEUE_REQUIRED' -MetricName 'count'

        $qGenerated = [int]$runGenerated
        $passing = [int]$runPassed
        $errors = [int]$runAborted
        $qSkipped = [int]$runSkipped
        $qQueued = [Math]::Max(0, ([int]$qGenerated + [int]$passing - [int]$errors + [int]$qSkipped))
      }
    }

    return [PSCustomObject]@{
      reviewed = $ingested
      advanced = $advanced
      passed = $passing
      aborted = $errors
      q_generated = $qGenerated
      q_queued = $qQueued
      q_skipped = $qSkipped
      is_live = $true
    }
  } catch {
    return $null
  }
}

function Send-QuandalfCard {
  param(
    [string]$StatusWord,
    [string]$DurationLabel,
    [string]$RunId,
    [string]$NoteSentence
  )

  $cfg = Get-TelegramLogConfig
  if ($null -eq $cfg) { return }
  $bannerPath = Get-QuandalfBannerPath
  if ([string]::IsNullOrWhiteSpace($bannerPath)) { return }

  $orderInfo = Get-CurrentOrderInfo
  $resultsInfo = Get-ResultsReviewInfo
  $liveInfo = Get-LiveReviewInfo -RunId $RunId
  if ($null -ne $liveInfo -and $liveInfo.is_live) {
    $resultsInfo = $liveInfo
  }

  $iconOk = [char]0x2705
  $iconWarn = ([char]0x26A0) + ([char]0xFE0F)
  $iconFail = [char]0x274C
  $statusIcon = if ($StatusWord -eq 'ok') { $iconOk } elseif ($StatusWord -eq 'warn') { $iconWarn } else { $iconFail }

  $mirrorEmoji = [System.Char]::ConvertFromUtf32(0x1FA9E)
  $activityDivider = ([char]0x25CB) + (([string][char]0x2500) * 3) + 'activity' + (([string][char]0x2500) * 21)
  $noteDivider = ([char]0x25CB) + (([string][char]0x2500) * 3) + 'note' + (([string][char]0x2500) * 25)

  $lines = @()
  $lines += ($mirrorEmoji + ' Reflecting')
  $lines += ('Status: ' + $statusIcon + ' | Duration: ' + $DurationLabel)
  $lines += $activityDivider
  $queuedValue = 0
  try {
    if ($null -ne $resultsInfo.q_queued) { $queuedValue = [int]$resultsInfo.q_queued }
    else { $queuedValue = [int]$orderInfo.queued }
  } catch { $queuedValue = [int]$orderInfo.queued }

  $lines += ('Promoted: ' + [int]$resultsInfo.advanced)
  $lines += ('Passed: ' + [int]$resultsInfo.passed)
  $lines += ('Aborted: ' + [int]$resultsInfo.aborted)
  $lines += ('Generated: ' + [int]$resultsInfo.q_generated)
  $lines += ('Queued: ' + [int]$queuedValue)
  $lines += $noteDivider
  $lines += $NoteSentence

  $messageBody = ($lines -join "`n").TrimEnd()
  $escaped = Escape-Html -Text $messageBody
  if ($escaped.Length -gt 985) { $escaped = $escaped.Substring(0, 982) + '...' }
  $caption = '<pre>' + $escaped + '</pre>'

  $uri = 'https://api.telegram.org/bot' + $cfg.token + '/sendPhoto'
  $boundary = [System.Guid]::NewGuid().ToString()
  $parts = @()
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"chat_id`"`r`n`r`n$($cfg.chat_id)"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"caption`"`r`n`r`n$caption"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"parse_mode`"`r`n`r`nHTML"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"photo`"; filename=`"quandalf_banner.jpg`"`r`nContent-Type: image/jpeg`r`n"

  $preBytes = [System.Text.Encoding]::UTF8.GetBytes(($parts -join "`r`n") + "`r`n")
  $photoBytes = [System.IO.File]::ReadAllBytes($bannerPath)
  $endBytes = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
  $fullBody = New-Object byte[] ($preBytes.Length + $photoBytes.Length + $endBytes.Length)
  [System.Buffer]::BlockCopy($preBytes, 0, $fullBody, 0, $preBytes.Length)
  [System.Buffer]::BlockCopy($photoBytes, 0, $fullBody, $preBytes.Length, $photoBytes.Length)
  [System.Buffer]::BlockCopy($endBytes, 0, $fullBody, ($preBytes.Length + $photoBytes.Length), $endBytes.Length)

  Invoke-RestMethod -Uri $uri -Method Post -Body $fullBody -ContentType ("multipart/form-data; boundary=" + $boundary) | Out-Null
}

function Get-LatestQuandalfCronEntry {
  try {
    $raw = & openclaw cron runs --id $jobId --limit 1
    $obj = $raw | ConvertFrom-Json
    if ($obj -and $obj.entries -and $obj.entries.Count -gt 0) {
      return $obj.entries[0]
    }
  } catch {}
  return $null
}

function Format-DurationLabelFromMs {
  param([Nullable[Int64]]$DurationMs)
  if ($null -eq $DurationMs) { return '0m 00s' }
  $ms = [int64]$DurationMs
  if ($ms -lt 0) { $ms = 0 }
  $mins = [int][Math]::Floor($ms / 60000)
  $secs = [int][Math]::Floor(($ms % 60000) / 1000)
  return ($mins.ToString() + 'm ' + $secs.ToString('00') + 's')
}

function Get-HyperMode {
  if (-not (Test-Path -LiteralPath $runtimeFlagsPath)) { return $false }
  try {
    $flags = Get-Content -LiteralPath $runtimeFlagsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($flags -and $flags.PSObject.Properties.Name -contains 'hyperMode') {
      return [bool]$flags.hyperMode
    }
  } catch {}
  return $false
}

function Get-RunSequence {
  param([string]$RunId)
  if ([string]::IsNullOrWhiteSpace($RunId)) { return -1 }
  if ($RunId -match '^autopilot-(\d+)') {
    try { return [int64]$matches[1] } catch { return -1 }
  }
  return -1
}

function Test-AutopilotProcessRunning {
  try {
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
      ($_.Name -match 'powershell') -and (
        ($_.CommandLine -match 'autopilot_worker\.ps1') -or
        ($_.CommandLine -match 'run_autopilot_task\.ps1')
      )
    }
    return (@($procs).Count -gt 0)
  } catch {
    return $false
  }
}

function Get-RunLastTimestampUtc {
  param([string]$RunId)
  if ([string]::IsNullOrWhiteSpace($RunId)) { return $null }
  if (-not (Test-Path -LiteralPath $actionsPath)) { return $null }

  $hits = @()
  try {
    $rows = Get-Content -LiteralPath $actionsPath -Tail 5000 -Encoding UTF8
    foreach ($line in $rows) {
      try { $e = $line | ConvertFrom-Json } catch { continue }
      $rid = [string]$e.run_id
      if (-not $rid.StartsWith($RunId + '-')) { continue }
      $tsRaw = [string]$e.ts_iso
      if ([string]::IsNullOrWhiteSpace($tsRaw)) { continue }
      try { $hits += [DateTime]::Parse($tsRaw).ToUniversalTime() } catch {}
    }
  } catch {}

  if (@($hits).Count -eq 0) { return $null }
  return (@($hits | Sort-Object) | Select-Object -Last 1)
}

function Wait-ForFrodexRunSettle {
  param(
    [string]$RunId,
    [int]$TimeoutSeconds = 180,
    [int]$QuietSeconds = 4
  )

  $deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(10, $TimeoutSeconds))
  $lastReason = 'unknown'

  while ([DateTime]::UtcNow -lt $deadline) {
    if (Test-Path -LiteralPath $autopilotWorkerLockPath) {
      $lastReason = 'autopilot lock still present'
      Start-Sleep -Seconds 2
      continue
    }

    if (Test-AutopilotProcessRunning) {
      $lastReason = 'autopilot process still running'
      Start-Sleep -Seconds 2
      continue
    }

    $lastTs = Get-RunLastTimestampUtc -RunId $RunId
    if ($null -eq $lastTs) {
      $lastReason = 'no run events found yet'
      Start-Sleep -Seconds 2
      continue
    }

    $ageSec = ([DateTime]::UtcNow - $lastTs).TotalSeconds
    if ($ageSec -lt $QuietSeconds) {
      $lastReason = ('run still hot (' + [int][Math]::Floor($ageSec) + 's since last event)')
      Start-Sleep -Seconds 2
      continue
    }

    return [PSCustomObject]@{ ok = $true; reason = 'settled'; age_seconds = [int][Math]::Floor($ageSec) }
  }

  return [PSCustomObject]@{ ok = $false; reason = $lastReason; age_seconds = -1 }
}

function Test-HandoffPollProcessRunning {
  try {
    $selfPid = $PID
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
      ($_.ProcessId -ne $selfPid) -and ($_.Name -match 'powershell') -and ($_.CommandLine -match 'check_quandalf_handoff\.ps1')
    }
    return (@($procs).Count -gt 0)
  } catch {
    return $false
  }
}

New-Item -ItemType Directory -Force -Path (Split-Path $statePath -Parent) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $lockDir -Parent) | Out-Null

if (Test-Path -LiteralPath $lockDir) {
  $activePoll = Test-HandoffPollProcessRunning
  if (-not $activePoll) {
    try {
      Remove-Item -LiteralPath $lockDir -Recurse -Force -ErrorAction SilentlyContinue
      Write-Host 'Recovered stale handoff poll lock.'
    } catch {}
  }
}

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

  $hyperMode = Get-HyperMode
  $lastTriggered = ''
  if (Test-Path -LiteralPath $statePath) {
    try {
      $st = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
      if ($st -and $st.PSObject.Properties.Name -contains 'last_triggered_run_id') {
        $lastTriggered = [string]$st.last_triggered_run_id
      }
    } catch {}
  }

  # In hyper mode, trust explicit handoff target from caller to avoid state drift races.
  if ($hyperMode -and -not [string]::IsNullOrWhiteSpace($RunIdHint)) {
    $latestRunId = [string]$RunIdHint
  }

  if ([string]::IsNullOrWhiteSpace($latestRunId)) {
    Write-Host 'No completed Frodex run found.'
    exit 0
  }

  if ($lastTriggered -eq $latestRunId) {
    Write-Host ('No new run. latest=' + $latestRunId)
    exit 0
  }

  Write-Host ('New completed run detected: ' + $latestRunId + ' -> triggering quandalf-auto-execute')

  # Ensure Frodex run is fully settled before handoff trigger.
  $settle = Wait-ForFrodexRunSettle -RunId $latestRunId -TimeoutSeconds $settleTimeoutSeconds -QuietSeconds $settleQuietSeconds
  if (-not $settle.ok) {
    $note = ('Upstream run has not settled yet (' + [string]$settle.reason + '), so I deferred this handoff and will retry shortly.')
    Send-QuandalfCard -StatusWord 'warn' -DurationLabel '0m 00s' -RunId $latestRunId -NoteSentence $note
    Write-Host ('WARN handoff deferred for run ' + $latestRunId + ': ' + [string]$settle.reason)
    exit 0
  }

  if ($handoffBufferSeconds -gt 0) {
    Start-Sleep -Seconds $handoffBufferSeconds
  }

  $triggerStarted = Get-Date
  $triggerOutput = @(& openclaw cron run $jobId --timeout 120000 2>&1)
  if ($LASTEXITCODE -ne 0) {
    # retry once with a short backoff for transient gateway pressure
    Start-Sleep -Seconds 5
    $triggerOutput = @(& openclaw cron run $jobId --timeout 120000 2>&1)
  }
  if ($LASTEXITCODE -ne 0) {
    $triggerText = ($triggerOutput -join ' ')
    $note = 'Triggering reflection timed out at the gateway; I will retry on the next completed run.'
    if ($triggerText -match '(?i)model not allowed') {
      $note = 'Reflection trigger was blocked by model policy, so this cycle fell back and will retry on the next run.'
    } elseif ($triggerText -match '(?i)lock') {
      $note = 'Reflection trigger skipped because another run was already active; it will retry next cycle.'
    }
    Send-QuandalfCard -StatusWord 'warn' -DurationLabel '0m 00s' -RunId $latestRunId -NoteSentence $note
    if ($hyperMode) {
      $failState = @{
        last_triggered_run_id = $lastTriggered
        last_failed_run_id = $latestRunId
        updated_at = [DateTime]::UtcNow.ToString('o')
      }
      ($failState | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $statePath -Encoding UTF8
    }
    Write-Host ('WARN trigger failed for run ' + $latestRunId + ': ' + $triggerText)
    exit 0
  }

  Start-Sleep -Milliseconds 400
  $entry = Get-LatestQuandalfCronEntry
  $statusWord = 'ok'
  $durLabel = '0m 00s'
  $noteSentence = 'I completed the reflection cycle and updated the latest strategy context for the next run.'

  if ($entry) {
    $statusWord = [string]$entry.status

    # Quandalf duration contract: handoff emitted -> quandalf run finished.
    $durLabel = Format-DurationLabelFromMs -DurationMs ([Nullable[Int64]]$entry.durationMs)
    $handoffTsUtc = Get-RunHandoffTimestampUtc -RunId $latestRunId
    if ($null -ne $handoffTsUtc -and $null -ne $entry.ts) {
      try {
        $finishUtc = [DateTimeOffset]::FromUnixTimeMilliseconds([int64]$entry.ts).UtcDateTime
        $deltaMs = [int64][Math]::Round(($finishUtc - $handoffTsUtc).TotalMilliseconds)
        if ($deltaMs -ge 0) {
          $durLabel = Format-DurationLabelFromMs -DurationMs ([Nullable[Int64]]$deltaMs)
        }
      } catch {}
    }

    $summary = [string]$entry.summary
    $liveNow = Get-LiveReviewInfo -RunId $latestRunId
    $qGenNow = 0
    $qQueuedNow = 0
    $qSkippedNow = 0
    if ($null -ne $liveNow) {
      try { $qGenNow = [int]$liveNow.q_generated } catch {}
      try { $qQueuedNow = [int]$liveNow.q_queued } catch {}
      try { $qSkippedNow = [int]$liveNow.q_skipped } catch {}
    }

    if ($statusWord -ne 'ok') {
      $entryError = [string]$entry.error
      if ($entryError -match '(?i)gateway timeout') {
        $noteSentence = 'Reflection was delayed by a gateway timeout, and the pipeline will retry automatically on the next run.'
      } elseif ($entryError -match '(?i)model not allowed') {
        $noteSentence = 'Reflection was blocked by model policy for this attempt; fallback routing is in place and the next run will retry.'
      } elseif (-not [string]::IsNullOrWhiteSpace($entryError)) {
        $noteSentence = ('Reflection cycle hit an execution issue: ' + $entryError + '. It will retry on the next completed run.')
      } else {
        $noteSentence = 'Cycle hit an execution issue; remediation is required before throughput can normalize.'
      }
    } elseif ($qSkippedNow -gt 0) {
      $noteSentence = ('Frodex skipped ' + [int]$qSkippedNow + ' strategy test(s); Quandalf must rectify or abort those items next cycle.')
    } elseif ($qGenNow -eq 0 -and $qQueuedNow -eq 0) {
      $noteSentence = 'No novel strategies generated or queued this cycle - generation contract breached.'
    } elseif ($qGenNow -eq 0 -and $qQueuedNow -gt 0) {
      $noteSentence = ('No new generation this cycle; ' + [int]$qQueuedNow + ' strategies remain queued for testing.')
    } else {
      $noteSentence = ('Generated ' + [int]$qGenNow + ' novel strategies and queued ' + [int]$qQueuedNow + ' for testing.')
    }

    if (($summary -match '(?i)no pending order') -and $qGenNow -eq 0 -and $qQueuedNow -eq 0) {
      $noteSentence = 'No pending strategy order and no generation/queue activity this cycle.'
    }
  } else {
    $durLabel = Format-DurationLabelFromMs -DurationMs ([Nullable[Int64]]((New-TimeSpan -Start $triggerStarted -End (Get-Date)).TotalMilliseconds))
  }

  $reflectionStatus = Get-ReflectionStatusForRun -RunId $latestRunId
  if ($null -ne $reflectionStatus -and [string]$reflectionStatus.status -eq 'fallback_gpt') {
    $noteSentence = $noteSentence + ' ⚠️ Claude reflection failed; GPT fallback path was used.'
  }

  Send-QuandalfCard -StatusWord $statusWord -DurationLabel $durLabel -RunId $latestRunId -NoteSentence $noteSentence

  $state = @{
    last_triggered_run_id = $latestRunId
    last_failed_run_id = ''
    updated_at = [DateTime]::UtcNow.ToString('o')
  }
  ($state | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $statePath -Encoding UTF8
  Write-Host ('Triggered for run ' + $latestRunId)
}
finally {
  Remove-Item -LiteralPath $lockDir -Recurse -Force -ErrorAction SilentlyContinue
}

