# Bundled Run Log — one photo+caption per pipeline cycle to LOG CHANNEL
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

# Read gateway bot token and log channel from workspace .env
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

$LOG_CHANNEL = $logChannel

# Read last 120 min of actions (testing)
$logPath = "$ROOT\data\logs\actions.ndjson"
if (-not (Test-Path $logPath)) { Write-Host "No action log"; exit 0 }
$cutoff = (Get-Date).AddMinutes(-16).ToUniversalTime()
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

# Determine primary agent for banner
$agents = @($events | ForEach-Object { $_.agent } | Where-Object { $_ } | Sort-Object -Unique)
$quandalfAgents = @("claude-advisor", "claude-researcher", "claude-iterator")
$hasQuandalf = $agents | Where-Object { $_ -in $quandalfAgents }
$primaryAgent = if ($hasQuandalf) { "quandalf" } else { "frodex" }

# Find banner (check multiple extensions)
$bannerPath = $null
$bannerDir = "$ROOT\assets\banners"
foreach ($ext in @("png", "jpg", "png.jpg", "jpeg", "webp")) {
  $tryPath = "$bannerDir\${primaryAgent}_banner.$ext"
  if (Test-Path $tryPath) { $bannerPath = $tryPath; break }
}

# Count statuses
$failCount = 0
$warnCount = 0
foreach ($e in $events) {
  $s = if ($e.status_word) { $e.status_word.ToUpper() } else { "OK" }
  if ($s -eq "FAIL") { $failCount++ }
  if ($s -eq "WARN") { $warnCount++ }
}
$overallStatus = if ($failCount -gt 0) { "FAIL" } elseif ($warnCount -gt 0) { "WARN" } else { "OK" }
$overallEmoji = switch ($overallStatus) {
  "OK" { [char]::ConvertFromUtf32(0x2705) }
  "WARN" { [char]::ConvertFromUtf32(0x26A0) }
  "FAIL" { [char]::ConvertFromUtf32(0x274C) }
  default { [char]::ConvertFromUtf32(0x2705) }
}
$ts = Get-Date -Format "h:mm tt"

$lines = @()
$lines += "$overallEmoji Pipeline Cycle - $ts"
$lines += ""

# Filter out Logger/audit noise and INFO-only diagnostics
$mainEvents = @($events | Where-Object {
  $a = if ($_.agent) { $_.agent } else { "" }
  $act = if ($_.action) { $_.action } else { "" }
  ($a -ne "Logger") -and ($act -notmatch "AUDIT|DIAG")
})
if ($mainEvents.Count -eq 0) { Write-Host "No meaningful events"; exit 0 }

# Extract key metrics from SUMMARY events
$grabbed = 0; $grabFailed = 0
$btRuns = 0; $btExecuted = 0; $btSkipped = 0
$promoted = 0; $promoBundles = 0
$refined = 0; $refExplored = 0
$librarySize = 0; $libNew = 0; $libLessons = 0
$dirNotes = 0; $dirVariants = 0; $dirExplore = 0
$ingested = 0; $errors = 0
$insightNew = 0
$warnings = @()
$stall = 0; $starvation = 0

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
      if ($sum -match 'bundles=(\d+)') { $promoBundles = [int]$matches[1] }
      if ($sum -match 'variants=(\d+)') { $promoted = [int]$matches[1] }
    }
    "REFINEMENT_SUMMARY" {
      if ($sum -match 'iters=(\d+)') { $refined = [int]$matches[1] }
      if ($sum -match 'explore=(\d+)') { $refExplored = [int]$matches[1] }
    }
    "DIRECTIVE_LOOP_SUMMARY" {
      if ($sum -match 'notes=(\d+)') { $dirNotes = [int]$matches[1] }
      if ($sum -match 'directive_variants=(\d+)') { $dirVariants = [int]$matches[1] }
      if ($sum -match 'exploration_variants=(\d+)') { $dirExplore = [int]$matches[1] }
    }
    "LAB_SUMMARY" {
      if ($sum -match 'ingested=(\d+)') { $ingested = [int]$matches[1] }
      if ($sum -match 'errors=(\d+)') { $errors = [int]$matches[1] }
    }
    "INSIGHT_SUMMARY" {
      if ($sum -match 'new_processed=(\d+)') { $insightNew = [int]$matches[1] }
    }
  }

  # Track stall/starvation from any event
  if ($sum -match 'stall.*?(\d+)\s*cycle') { $stall = [int]$matches[1] }
  if ($sum -match 'starvation[=:\s]+(\d+)') { $starvation = [int]$matches[1] }

  # Collect warnings
  if ($stat -in @("WARN", "FAIL", "BLOCKED")) {
    $reason = if ($e.reason_code) { $e.reason_code } else { "unknown" }
    $warnings += "$($e.agent): $reason"
  }
}

# Build clean message
$warnEmoji = [char]::ConvertFromUtf32(0x26A0)
$okEmoji = [char]::ConvertFromUtf32(0x2705)
$failEmoji = [char]::ConvertFromUtf32(0x274C)
$hasProblems = ($errors -gt 0) -or ($stall -gt 5) -or ($starvation -gt 10) -or ($warnings.Count -gt 0)
$headerEmoji = if ($errors -gt 0) { $failEmoji } elseif ($hasProblems) { $warnEmoji } else { $okEmoji }
$ts = Get-Date -Format "h:mm tt"

$lines = @()
$lines += "$headerEmoji Frodex Pipeline $ts"
$lines += ""

# Only show lines with something to report
if ($grabbed -gt 0 -or $grabFailed -gt 0) {
  $grabLine = "Videos grabbed: $grabbed"
  if ($grabFailed -gt 0) { $grabLine += " ($grabFailed failed)" }
  $lines += $grabLine
}
if ($ingested -gt 0) { $lines += "Specs ingested: $ingested" }
if ($btExecuted -gt 0 -or $btRuns -gt 0) {
  $lines += "Backtested: $btExecuted runs"
} elseif ($btSkipped -gt 0) {
  $lines += "Backtests: skipped (no variants)"
}
if ($refined -gt 0) { $lines += "Refined: $refined iterations" }
if ($promoted -gt 0) { $lines += "Promoted: $promoted strategies" }
if ($dirVariants -gt 0 -or $dirExplore -gt 0) { $lines += "New variants: $dirVariants directive + $dirExplore exploration" }
if ($libNew -gt 0) { $lines += "Library: $librarySize (+$libNew new)" }
if ($insightNew -gt 0) { $lines += "Insights: $insightNew processed" }

# Always show problems
if ($stall -gt 5) { $lines += "$warnEmoji Directive stall: $stall cycles" }
if ($starvation -gt 10) { $lines += "$warnEmoji Starvation: $starvation cycles" }
if ($errors -gt 0) { $lines += "$failEmoji Errors: $errors" }

# Deduplicated warnings
if ($warnings.Count -gt 0) {
  $uniqueWarnings = @{}
  foreach ($w in $warnings) {
    $cur = if ($uniqueWarnings.ContainsKey($w)) { $uniqueWarnings[$w] } else { 0 }
    $uniqueWarnings[$w] = $cur + 1
  }

  # Only show if not already covered by stall/starvation
  $filteredWarnings = @($uniqueWarnings.GetEnumerator() | Where-Object { $_.Key -notmatch "STALL|STARVATION" } | Sort-Object Value -Descending | Select-Object -First 3)
  foreach ($fw in $filteredWarnings) {
    $countSuffix = if ($fw.Value -gt 1) { " (x$($fw.Value))" } else { "" }
    $lines += "$warnEmoji $($fw.Key)$countSuffix"
  }
}

# If nothing happened at all
if ($lines.Count -le 2) {
  $lines += "Idle cycle - nothing to process"
}

$caption = ($lines -join "`n").TrimEnd()

# Send as photo+caption to LOG CHANNEL
if ($bannerPath) {
  $uri = "https://api.telegram.org/bot$token/sendPhoto"
  $boundary = [System.Guid]::NewGuid().ToString()
  $bodyLines = @()
  $bodyLines += "--$boundary"
  $bodyLines += 'Content-Disposition: form-data; name="chat_id"'
  $bodyLines += ""
  $bodyLines += $LOG_CHANNEL
  $bodyLines += "--$boundary"
  $bodyLines += 'Content-Disposition: form-data; name="caption"'
  $bodyLines += ""
  $bodyLines += $caption
  $bodyLines += "--$boundary"
  $bodyLines += 'Content-Disposition: form-data; name="photo"; filename="banner.png"'
  $bodyLines += "Content-Type: image/png"
  $bodyLines += ""

  $bodyText = ($bodyLines -join "`r`n") + "`r`n"
  $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($bodyText)
  $photoBytes = [System.IO.File]::ReadAllBytes($bannerPath)
  $endBytes = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
  $fullBody = New-Object byte[] ($bodyBytes.Length + $photoBytes.Length + $endBytes.Length)
  [System.Buffer]::BlockCopy($bodyBytes, 0, $fullBody, 0, $bodyBytes.Length)
  [System.Buffer]::BlockCopy($photoBytes, 0, $fullBody, $bodyBytes.Length, $photoBytes.Length)
  [System.Buffer]::BlockCopy($endBytes, 0, $fullBody, ($bodyBytes.Length + $photoBytes.Length), $endBytes.Length)

  try {
    Invoke-RestMethod -Uri $uri -Method Post -Body $fullBody -ContentType "multipart/form-data; boundary=$boundary" | Out-Null
    Write-Host "Bundle sent to log channel with banner"
  } catch {
    $textUri = "https://api.telegram.org/bot$token/sendMessage"
    $textBody = @{ chat_id = $LOG_CHANNEL; text = $caption } | ConvertTo-Json -Compress
    Invoke-RestMethod -Uri $textUri -Method Post -Body $textBody -ContentType "application/json" | Out-Null
    Write-Host "Banner failed, sent as text to log channel"
  }
} else {
  $uri = "https://api.telegram.org/bot$token/sendMessage"
  $body = @{ chat_id = $LOG_CHANNEL; text = $caption } | ConvertTo-Json -Compress
  Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" | Out-Null
  Write-Host "Bundle sent as text to log channel (no banner)"
}

$caption | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
Write-Host "Done"