param()

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
    return [PSCustomObject]@{ reviewed = $reviewed; advanced = $advanced; aborted = $aborted; is_live = $false }
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

  return [PSCustomObject]@{ reviewed = $reviewed; advanced = $advanced; aborted = $aborted; is_live = $false }
}

function Get-LiveReviewInfo {
  if (-not (Test-Path -LiteralPath $autopilotSummaryPath)) {
    return $null
  }

  try {
    $s = Get-Content -LiteralPath $autopilotSummaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $s) { return $null }

    $ingested = [int]($s.candidates_ingested)
    $passing = [int]($s.candidates_passing_gate)
    $errors = [int]($s.errors_count)

    return [PSCustomObject]@{
      reviewed = $ingested
      advanced = $passing
      aborted = $errors
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
  $liveInfo = Get-LiveReviewInfo
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
  $lines += ('Reviewed: ' + [int]$resultsInfo.reviewed)
  $lines += ('Advanced: ' + [int]$resultsInfo.advanced)
  $lines += ('Aborted: ' + [int]$resultsInfo.aborted)
  $lines += ('Queued: ' + [int]$orderInfo.queued)
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
    Write-Host ('No new run. latest=' + $latestRunId)
    exit 0
  }

  Write-Host ('New completed run detected: ' + $latestRunId + ' -> triggering quandalf-auto-execute')
  $triggerStarted = Get-Date
  & openclaw cron run $jobId --timeout 120000 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Send-QuandalfCard -StatusWord 'fail' -DurationLabel '0m 00s' -RunId $latestRunId -NoteSentence 'I could not execute this reflection cycle due to a trigger failure, and I will retry on the next completed run.'
    throw ('openclaw cron run failed with code ' + $LASTEXITCODE)
  }

  Start-Sleep -Milliseconds 400
  $entry = Get-LatestQuandalfCronEntry
  $statusWord = 'ok'
  $durLabel = '0m 00s'
  $noteSentence = 'I completed the reflection cycle and updated the latest strategy context for the next run.'

  if ($entry) {
    $statusWord = [string]$entry.status
    $durLabel = Format-DurationLabelFromMs -DurationMs ([Nullable[Int64]]$entry.durationMs)
    $summary = [string]$entry.summary

    if ($summary -match '(?i)no pending order') {
      $noteSentence = 'There was no queued strategy order for this cycle, so I reviewed outcomes and stayed ready for the next completed run.'
    } elseif ($statusWord -ne 'ok') {
      $noteSentence = 'I hit an execution issue in this reflection cycle and captured it for immediate follow-up.'
    } else {
      $noteSentence = 'I processed the queued strategy work and refreshed the result set for the next decision cycle.'
    }
  } else {
    $durLabel = Format-DurationLabelFromMs -DurationMs ([Nullable[Int64]]((New-TimeSpan -Start $triggerStarted -End (Get-Date)).TotalMilliseconds))
  }

  Send-QuandalfCard -StatusWord $statusWord -DurationLabel $durLabel -RunId $latestRunId -NoteSentence $noteSentence

  $state = @{
    last_triggered_run_id = $latestRunId
    updated_at = [DateTime]::UtcNow.ToString('o')
  }
  ($state | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $statePath -Encoding UTF8
  Write-Host ('Triggered for run ' + $latestRunId)
}
finally {
  Remove-Item -LiteralPath $lockDir -Recurse -Force -ErrorAction SilentlyContinue
}
