# Bundled Run Log — one photo+caption per pipeline cycle to LOG CHANNEL
# Default mode is Frodex (15-min lab loop). Optional Quandalf mode for Claude windows.

param(
  [ValidateSet('frodex','quandalf')]
  [string]$Pipeline = 'frodex',
  [int]$WindowMinutes = 16
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

# --- Config from .env ---
$wsEnv = "$ROOT\.env"
if (-not (Test-Path $wsEnv)) { Write-Host "No workspace .env"; exit 1 }

$token = $null
$logChannel = $null
Get-Content $wsEnv | ForEach-Object {
  if ($_ -match '^TELEGRAM_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  if ($_ -match '^TELEGRAM_LOG_CHAT_ID=(.*)$') { $logChannel = $matches[1].Trim() }
}
if (-not $token) { Write-Host "Missing bot token"; exit 1 }
if (-not $logChannel) { Write-Host "Missing log channel ID"; exit 1 }

# --- Read events from recent window ---
$logPath = "$ROOT\data\logs\actions.ndjson"
if (-not (Test-Path $logPath)) { Write-Host "No action log"; exit 0 }

$effectiveWindow = if ($WindowMinutes -lt 1) { 1 } else { $WindowMinutes }
$cutoff = (Get-Date).AddMinutes(-1 * $effectiveWindow).ToUniversalTime()
$events = @()
foreach ($line in (Get-Content $logPath -Encoding UTF8 -Tail 300)) {
  try {
    $entry = $line | ConvertFrom-Json
    $tsRaw = if ($entry.ts_iso) { $entry.ts_iso } elseif ($entry.ts) { $entry.ts } else { $null }
    if (-not $tsRaw) { continue }
    try { $ts = [DateTime]::Parse($tsRaw).ToUniversalTime() } catch { continue }
    if ($ts -ge $cutoff) { $events += $entry }
  } catch { continue }
}
if ($events.Count -eq 0) { Write-Host "No events in window"; exit 0 }

# --- Filter noise + pipeline ownership ---
$mode = $Pipeline.ToLowerInvariant()
$mainEvents = @($events | Where-Object {
  $a = if ($_.agent) { [string]$_.agent } else { "" }
  $act = if ($_.action) { [string]$_.action } else { "" }
  if (($a -eq "Logger") -or ($act -match "AUDIT|DIAG")) { return $false }

  if ($mode -eq 'quandalf') {
    # Quandalf-owned stream (Claude strategist tasks)
    return ($a -match '(?i)claude|quandalf')
  }

  # Frodex-owned stream: explicitly exclude Claude/Quandalf entries
  return -not ($a -match '(?i)claude|quandalf')
})
if ($mainEvents.Count -eq 0) { Write-Host "No meaningful events for pipeline=$mode"; exit 0 }

# --- Banner selection ---
$primaryAgent = if ($mode -eq 'quandalf') { "quandalf" } else { "frodex" }

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

# --- Build message ---
$hasErrors = $errors -gt 0
$hasWarnings = ($stall -gt 5) -or ($starvation -gt 10) -or ($warnings.Count -gt 0)
$statusTag = if ($hasErrors) { "FAIL" } elseif ($hasWarnings) { "WARN" } else { "OK" }
$statusIcon = switch ($statusTag) {
  "OK" { "✅" }
  "WARN" { "⚠️" }
  "FAIL" { "❌" }
}

$ts = Get-Date -Format "h:mm tt"
$agentLabel = if ($mode -eq 'quandalf') { "Quandalf" } else { "Frodex" }

# Model label for header (abbrev)
$modelLabel = 'n/a'
$modelBuckets = @($mainEvents | ForEach-Object { [string]$_.model_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -ne 'system' } | Group-Object | Sort-Object Count -Descending)
if ($modelBuckets.Count -gt 0) {
  $modelRaw = [string]$modelBuckets[0].Name
  if ($modelRaw -match '(?i)gpt-5\.3') { $modelLabel = 'GPT 5.3' }
  elseif ($modelRaw -match '(?i)opus[-_ ]?4[-_ ]?6') { $modelLabel = 'Opus 4.6' }
  else {
    $modelLabel = $modelRaw
    if ($modelLabel.Length -gt 14) { $modelLabel = $modelLabel.Substring(0, 14) }
  }
}

$lines = @()
$lines += "$statusIcon $agentLabel $modelLabel $ts"
$lines += ("-" * 33)

if ($mode -eq 'quandalf') {
  # Strict action-mode metrics only (no inferred/regex-derived counts)
  $strategyGenerateCount = @($mainEvents | Where-Object { [string]$_.action -eq 'strategy_generate' }).Count
  $strategyResearchCount = @($mainEvents | Where-Object { [string]$_.action -eq 'strategy_research' }).Count
  $doctrineSynthesisCount = @($mainEvents | Where-Object { [string]$_.action -eq 'doctrine_synthesis' }).Count
  $backtestAuditCount = @($mainEvents | Where-Object { [string]$_.action -eq 'backtest_audit' }).Count
  $totalStrictRuns = $strategyGenerateCount + $strategyResearchCount + $doctrineSynthesisCount + $backtestAuditCount

  $lines += "Generated : $strategyGenerateCount runs"
  $lines += "Researched: $strategyResearchCount runs"
  $lines += "Doctrine : $doctrineSynthesisCount runs"
  $lines += "Audited : $backtestAuditCount runs"
  $lines += "Total    : $totalStrictRuns runs"
} else {
  $lines += "Grabbed : $grabbed videos$(if ($grabFailed -gt 0) { " ($grabFailed failed)" })"
  $lines += "Ingested : $ingested specs"
  if ($btExecuted -gt 0) { $lines += "Backtested: $btExecuted runs" } else { $lines += "Backtested: 0 (no variants)" }
  $lines += "Variants : $dirVariants new + $dirExplore explore"
  $lines += "Refined : $refined iterations"
  $lines += "Promoted : $promoted strategies"
  if ($insightNew -gt 0) { $lines += "Insights : $insightNew processed" }
}

# Shared bottom note block (up to 3 lines)
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
$recentRiskEvent = @($mainEvents | Where-Object { @('WARN','FAIL','BLOCKED') -contains ([string]$_.status_word).ToUpper() } | Select-Object -Last 1)
$recentRiskSummary = if ($recentRiskEvent.Count -gt 0) { ([string]$recentRiskEvent[0].summary -replace '\s+', ' ').Trim() } else { '' }

if ($errors -gt 0) {
  if (-not [string]::IsNullOrWhiteSpace($recentRiskSummary)) {
    $noteText = "I hit $errors issue(s). Latest: $recentRiskSummary"
  } else {
    $noteText = "I hit $errors issue(s) in this window and need a quick review."
  }
} elseif ($stall -gt 5) {
  $noteText = "I did not produce new variants for $stall cycles, so exploration is stalled."
} elseif ($starvation -gt 10) {
  $noteText = "I am input-starved for $starvation cycles, so throughput is constrained."
} elseif ($topWarning) {
  $noteText = "I flagged a warning to watch: $topWarning"
} else {
  if ($mode -eq 'quandalf') {
    if ($strategyGenerateCount -gt 0 -and $strategyResearchCount -eq 0 -and $doctrineSynthesisCount -eq 0 -and $backtestAuditCount -eq 0) {
      $noteText = "I focused on strategy generation this window and completed it cleanly."
    } elseif ($strategyResearchCount -gt 0 -and $strategyGenerateCount -eq 0) {
      $noteText = "I focused on research updates this window and completed them cleanly."
    } elseif ($totalStrictRuns -gt 0) {
      $noteText = "I completed planned Claude runs cleanly across generation/research/doctrine/audit."
    } else {
      $noteText = "No Claude runs were recorded in this window."
    }
  } else {
    if ($btExecuted -gt 0) {
      $noteText = "I advanced $btExecuted backtest run(s) this cycle and kept the pipeline stable."
    } elseif ($ingested -gt 0) {
      $noteText = "I ingested $ingested new item(s) this cycle; backtests will follow next stages."
    } elseif ($dirVariants -gt 0) {
      $noteText = "I emitted $dirVariants new variant(s) this cycle to keep exploration moving."
    } else {
      $noteText = "This cycle was quiet, but the pipeline remained healthy."
    }
  }
}

$noteText = ($noteText -replace '\s+', ' ').Trim()
if ($noteText.Length -gt 156) { $noteText = $noteText.Substring(0, 153) + '...' }

$maxLineLen = 46
$wrapped = @()
$current = ''
foreach ($word in ($noteText -split '\s+')) {
  if ([string]::IsNullOrWhiteSpace($word)) { continue }
  if ([string]::IsNullOrWhiteSpace($current)) {
    $current = $word
  } elseif (($current.Length + 1 + $word.Length) -le $maxLineLen) {
    $current = "$current $word"
  } else {
    $wrapped += $current
    $current = $word
    if ($wrapped.Count -ge 2) { break }
  }
}
if (-not [string]::IsNullOrWhiteSpace($current) -and $wrapped.Count -lt 3) { $wrapped += $current }
if ($wrapped.Count -eq 0) { $wrapped = @('All clear this cycle.') }
if ($wrapped.Count -gt 3) { $wrapped = @($wrapped | Select-Object -First 3) }

$lines += ("-" * 33)
$lines += ("Note: " + $wrapped[0])
if ($wrapped.Count -ge 2) { $lines += ("      " + $wrapped[1]) }
if ($wrapped.Count -ge 3) { $lines += ("      " + $wrapped[2]) }

$messageBody = ($lines -join "`n").TrimEnd()
$caption = "``````" + "`n" + $messageBody + "`n" + "``````"

# --- Send ---
function Send-TextMessage {
  param($tok, $chatId, $text)
  $uri = "https://api.telegram.org/bot$tok/sendMessage"
  $body = @{ chat_id = $chatId; text = $text; parse_mode = "Markdown" } | ConvertTo-Json -Compress
  Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" | Out-Null
}

if ($bannerPath) {
  $uri = "https://api.telegram.org/bot$token/sendPhoto"
  $boundary = [System.Guid]::NewGuid().ToString()
  $parts = @()
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"chat_id`"`r`n`r`n$logChannel"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"caption`"`r`n`r`n$caption"
  $parts += "--$boundary`r`nContent-Disposition: form-data; name=`"parse_mode`"`r`n`r`nMarkdown"
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