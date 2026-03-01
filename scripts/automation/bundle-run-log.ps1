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

$lines = @()
$lines += "$statusIcon $agentLabel Pipeline $ts"
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

# Shared bottom status block (max 2 lines)
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

$lines += ("-" * 33)
$lines += "Status : $statusIcon $statusTag (warnings=$($warnings.Count), errors=$errors)"
if ($errors -gt 0) {
  $lines += "Note   : Pipeline errors detected ($errors)"
} elseif ($stall -gt 5) {
  $lines += "Note   : No new variants for $stall cycles"
} elseif ($starvation -gt 10) {
  $lines += "Note   : Input starvation for $starvation cycles"
} elseif ($topWarning) {
  $lines += "Note   : $topWarning"
} else {
  $lines += "Note   : No active warnings"
}

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