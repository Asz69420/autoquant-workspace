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

# Group by agent, extract REAL numbers
$grouped = $events | Group-Object agent | Sort-Object Name
foreach ($g in $grouped) {
  $agent = $g.Name
  $agentEvents = $g.Group
  $combined = ($agentEvents | ForEach-Object { $_.summary } | Where-Object { $_ }) -join " "
  $actions = @($agentEvents | ForEach-Object { $_.action } | Where-Object { $_ } | Sort-Object -Unique)

  # Determine agent status
  $bestStatus = "OK"
  foreach ($ae in $agentEvents) {
    $s = if ($ae.status_word) { $ae.status_word.ToUpper() } else { "OK" }
    if ($s -eq "FAIL") { $bestStatus = "FAIL" }
    elseif ($s -eq "WARN" -and $bestStatus -ne "FAIL") { $bestStatus = "WARN" }
  }

  # Extract meaningful metrics from summary text
  $info = @()

  # Grabber
  if ($combined -match 'ingested[:\s=]+(\d+)') { $info += "ingested:$($matches[1])" }

  # Backtester
  if ($combined -match 'bundles[:\s=]+(\d+)') { $info += "backtested:$($matches[1])" }
  if ($combined -match 'passing_gate[:\s=]+(\d+)') { $info += "passed:$($matches[1])" }

  # Promotion
  if ($combined -match 'promotions[:\s=]+(\d+)') { $info += "promoted:$($matches[1])" }

  # Refinement
  if ($combined -match 'refinements[:\s=]+(\d+)') { $info += "refined:$($matches[1])" }
  if ($combined -match 'reached_refinement[:\s=]+(\d+)') { $info += "reached:$($matches[1])" }

  # Strategist / directives
  if ($combined -match 'directive_variants[:\s=]+(\d+)') { $info += "variants:$($matches[1])" }
  if ($combined -match 'exploration_variants[:\s=]+(\d+)') {
    $ev = $matches[1]
    if ([int]$ev -gt 0) { $info += "explored:$ev" }
  }

  # Library
  if ($combined -match 'active_library_size[:\s=]+(\d+)') { $info += "library:$($matches[1])" }

  # Librarian
  if ($combined -match 'top[:\s=]+(\d+)') { $info += "top:$($matches[1])" }
  if ($combined -match 'run[:\s=]+(\d+)') { $info += "run:$($matches[1])" }
  if ($combined -match 'lessons[:\s=]+(\d+)') { $info += "lessons:$($matches[1])" }

  # Errors
  if ($combined -match 'errors[:\s=]+(\d+)') {
    $errN = [int]$matches[1]
    if ($errN -gt 0) { $info += "ERRORS:$errN" }
  }

  # Stall warnings
  if ($combined -match 'stall.*?(\d+)\s*cycles') {
    $info += "stall:$($matches[1])cyc"
  } elseif ($combined -match 'stall[:\s=]+(\d+)') {
    $info += "stall:$($matches[1])"
  }

  # Starvation
  if ($combined -match 'starvation[:\s=]+(\d+)') {
    $starv = [int]$matches[1]
    if ($starv -gt 0) { $info += "starving:$starv" }
  }

  # Skip agents with no useful info and OK status
  if ($info.Count -eq 0 -and $bestStatus -eq "OK") { continue }

  # Remove zero-value metrics (noise)
  $info = @($info | Where-Object { $_ -notmatch ':0$' })

  # Skip if only zeros remained and status is OK
  if ($info.Count -eq 0 -and $bestStatus -eq "OK") { continue }

  # Status prefix
  $prefix = switch ($bestStatus) {
    "FAIL" { [char]::ConvertFromUtf32(0x274C) }
    "WARN" { [char]::ConvertFromUtf32(0x26A0) }
    default { [char]::ConvertFromUtf32(0x2705) }
  }

  $infoStr = if ($info.Count -gt 0) { $info -join " | " } else { "-" }
  $lines += "$prefix $agent : $infoStr"
}

# Warnings/errors detail at bottom
$failEvents = @($events | Where-Object {
  $s = if ($_.status_word) { $_.status_word.ToUpper() } else { "OK" }
  $s -in @("FAIL", "WARN", "BLOCKED")
})
if ($failEvents.Count -gt 0) {
  $lines += ""
  $seenReasons = @{}
  foreach ($fe in $failEvents) {
    $reason = if ($fe.reason_code) {
      $fe.reason_code
    } else {
      $sum = if ($fe.summary) { $fe.summary } else { "unknown" }
      $sum.Substring(0, [Math]::Min(50, $sum.Length))
    }
    $key = "$($fe.agent):$reason"
    if (-not $seenReasons.ContainsKey($key)) { $seenReasons[$key] = 0 }
    $seenReasons[$key]++
  }
  foreach ($sr in ($seenReasons.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 3)) {
    $warnEmoji = [char]::ConvertFromUtf32(0x26A0)
    $countSuffix = if ($sr.Value -gt 1) { " (x$($sr.Value))" } else { "" }
    $lines += "$warnEmoji $($sr.Key)$countSuffix"
  }
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