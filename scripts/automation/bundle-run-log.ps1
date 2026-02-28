# Bundled Run Log — one photo+caption per pipeline cycle to LOG CHANNEL
# Reads last 16 min of actions.ndjson, extracts metrics, sends clean summary

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

# --- Read events from last 16 minutes ---
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

# --- Filter noise ---
$mainEvents = @($events | Where-Object {
  $a = if ($_.agent) { $_.agent } else { "" }
  $act = if ($_.action) { $_.action } else { "" }
  ($a -ne "Logger") -and ($act -notmatch "AUDIT|DIAG")
})
if ($mainEvents.Count -eq 0) { Write-Host "No meaningful events"; exit 0 }

# --- Banner selection ---
$agents = @($mainEvents | ForEach-Object { $_.agent } | Where-Object { $_ } | Sort-Object -Unique)
$hasQuandalf = $false
foreach ($a in $agents) {
  if ($a -match "claude") { $hasQuandalf = $true; break }
}
$primaryAgent = if ($hasQuandalf) { "quandalf" } else { "frodex" }

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
    $reason = if ($e.reason_code) { $e.reason_code } else { "unknown" }
    $wKey = "$($e.agent): $reason"
    if ($wKey -notmatch "STALL|STARVATION") { $warnings += $wKey }
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
$agentLabel = if ($hasQuandalf) { "Quandalf" } else { "Frodex" }

$lines = @()
$lines += "$statusIcon $agentLabel Pipeline $ts"
$lines += ("-" * 34)
$lines += "Grabbed : $grabbed videos$(if ($grabFailed -gt 0) { " ($grabFailed failed)" })"
$lines += "Ingested : $ingested specs"
if ($btExecuted -gt 0) { $lines += "Backtested: $btExecuted runs" } else { $lines += "Backtested: 0 (no variants)" }
$lines += "Variants : $dirVariants new + $dirExplore explore"
$lines += "Refined : $refined iterations"
$lines += "Promoted : $promoted strategies"
if ($insightNew -gt 0) { $lines += "Insights : $insightNew processed" }
$lines += ("-" * 34)
$lines += "Library : $librarySize strats | $libLessons lessons"

if ($hasErrors -or $hasWarnings) {
  $lines += ("-" * 34)
  if ($stall -gt 5) { $lines += "⚠️ Stall: $stall cycles no variants" }
  if ($starvation -gt 10) { $lines += "⚠️ Starvation: $starvation cycles" }
  if ($errors -gt 0) { $lines += "❌ Errors: $errors" }

  $uniqueWarnings = @{}
  foreach ($w in $warnings) {
    $cur = if ($uniqueWarnings.ContainsKey($w)) { $uniqueWarnings[$w] } else { 0 }
    $uniqueWarnings[$w] = $cur + 1
  }

  $topWarnings = @($uniqueWarnings.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 3)
  foreach ($tw in $topWarnings) {
    $suffix = if ($tw.Value -gt 1) { " x$($tw.Value)" } else { "" }
    $lines += "⚠️ $($tw.Key)$suffix"
  }
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
    Write-Host "Photo failed: $_ - fallback to text"
    try { Send-TextMessage $token $logChannel $caption } catch { Write-Host "Text also failed: $_" }
  }
} else {
  try {
    Send-TextMessage $token $logChannel $caption
    Write-Host "Bundle sent as text (no banner)"
  } catch {
    Write-Host "Send failed: $_"
  }
}

$messageBody | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
Write-Host "Done"