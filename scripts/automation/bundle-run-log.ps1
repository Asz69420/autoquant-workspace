# Bundled Run Log — sends one Telegram photo+caption per pipeline cycle
# Reads last 15 min of actions.ndjson, bundles by agent, sends with banner
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT
$envFile = "$ROOT\scripts\claude-bridge\.env"
if (-not (Test-Path $envFile)) { Write-Host "No .env"; exit 1 }
$token = $null
$chatId = $null
Get-Content $envFile | ForEach-Object {
if ($_ -match '^CLAUDE_BRIDGE_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
if ($_ -match '^CLAUDE_BRIDGE_USER_ID=(.*)$') { $chatId = $matches[1].Trim() }
}
if (-not $token -or -not $chatId) { Write-Host "Missing creds"; exit 1 }
# Read last 15 min of actions
$logPath = "$ROOT\data\logs\actions.ndjson"
if (-not (Test-Path $logPath)) { Write-Host "No action log"; exit 0 }
$cutoff = (Get-Date).AddMinutes(-16).ToUniversalTime()
$events = @()
foreach ($line in (Get-Content $logPath -Encoding UTF8 -Tail 200)) {
try {
$entry = $line | ConvertFrom-Json
$ts = $null
try { $ts = [DateTime]::Parse($entry.ts).ToUniversalTime() } catch { continue }
if ($ts -ge $cutoff) { $events += $entry }
} catch { continue }
}
if ($events.Count -eq 0) { Write-Host "No events in window"; exit 0 }
# Determine primary agent
$agents = @($events | ForEach-Object { $_.agent } | Where-Object { $_ } | Sort-Object -Unique)
$hasQuandalf = $agents | Where-Object { $_ -match "claude" }
$primaryAgent = if ($hasQuandalf) { "quandalf" } else { "frodex" }
# Banner path
$bannerPath = "$ROOT\assets\banners\${primaryAgent}_banner.png"
if (-not (Test-Path $bannerPath)) { $bannerPath = $null }
# Build caption
$ts = Get-Date -Format "h:mm tt"
$statusCounts = @{ OK = 0; WARN = 0; FAIL = 0; BLOCKED = 0 }
foreach ($e in $events) {
$s = $(if ($e.status_word) { $e.status_word } else { "OK" }).ToUpper()
if ($statusCounts.ContainsKey($s)) { $statusCounts[$s]++ }
}
$overallStatus = if ($statusCounts.FAIL -gt 0) { "FAIL" } elseif ($statusCounts.BLOCKED -gt 0) { "BLOCKED" } elseif ($statusCounts.WARN -gt 0) { "WARN" } else { "OK" }
$statusEmoji = switch ($overallStatus) {
"OK" { [char]0x2705 }
"WARN" { [char]0x26A0 }
"FAIL" { [char]0x274C }
"BLOCKED" { [char]0x1F6AB }
}
$lines = @()
$lines += "$statusEmoji Pipeline Cycle - $ts"
$lines += ""
# Group by agent
$grouped = $events | Group-Object agent | Sort-Object Name
foreach ($g in $grouped) {
$agent = $g.Name
$agentEvents = $g.Group
$bestStatus = "OK"
foreach ($ae in $agentEvents) {
$s = $(if ($ae.status_word) { $ae.status_word } else { "OK" }).ToUpper()
if ($s -eq "FAIL") { $bestStatus = "FAIL" } elseif ($s -eq "WARN" -and $bestStatus -ne "FAIL") { $bestStatus = "WARN" }
}
$agentEmoji = switch ($bestStatus) {
"OK" { [char]0x2705 }
"WARN" { [char]0x26A0 }
"FAIL" { [char]0x274C }
default { [char]0x2705 }
}
# Extract key metrics from summaries
$summaries = @($agentEvents | ForEach-Object { $_.summary } | Where-Object { $_ })
$combined = ($summaries -join " ")
# Pull out interesting numbers
$metrics = @()
if ($combined -match 'profit_factor[:\s=]+(\d+\.?\d*)') { $metrics += "PF:$($matches[1])" }
if ($combined -match 'total_trades[:\s=]+(\d+)') { $metrics += "trades:$($matches[1])" }
if ($combined -match 'errors[:\s=]+(\d+)') {
$errCount = [int]$matches[1]
if ($errCount -gt 0) { $metrics += "errors:$errCount" }
}
if ($combined -match 'promotions[:\s=]+(\d+)') {
$promoCount = [int]$matches[1]
if ($promoCount -gt 0) { $metrics += "promoted:$promoCount" }
}
if ($combined -match 'active_library_size[:\s=]+(\d+)') { $metrics += "library:$($matches[1])" }
if ($combined -match 'bundles[:\s=]+(\d+)') {
$bCount = [int]$matches[1]
if ($bCount -gt 0) { $metrics += "backtested:$bCount" }
}
if ($combined -match 'stall[:\s=]+(\d+)') {
$stallCount = [int]$matches[1]
if ($stallCount -gt 0) { $metrics += "stall:$stallCount" }
}
$metricsStr = if ($metrics.Count -gt 0) { ($metrics -join " | ") } else { "ok" }
$lines += "$agentEmoji $agent - $metricsStr"
}
# Error summary
if ($statusCounts.FAIL -gt 0 -or $statusCounts.WARN -gt 0) {
$lines += ""
$failEvents = @($events | Where-Object { $(if ($_.status_word) { $_.status_word } else { "" }).ToUpper() -in @("FAIL", "WARN") })
foreach ($fe in ($failEvents | Select-Object -First 3)) {
$reason = if ($fe.reason_code) { $fe.reason_code } else { $(if ($fe.summary) { $fe.summary } else { "unknown" }).Substring(0, [Math]::Min(60, $(if ($fe.summary) { $fe.summary } else { "unknown" }).Length)) }
$lines += " $(([char]0x26A0)) $($fe.agent): $reason"
}
}
$caption = ($lines -join "`n").TrimEnd()
# Send as photo+caption or text
if ($bannerPath) {
$uri = "https://api.telegram.org/bot$token/sendPhoto"
$form = @{
chat_id = $chatId
caption = $caption
photo = [System.IO.File]::ReadAllBytes($bannerPath)
}
# Multipart form upload
$boundary = [System.Guid]::NewGuid().ToString()
$bodyLines = @()
$bodyLines += "--$boundary"
$bodyLines += 'Content-Disposition: form-data; name="chat_id"'
$bodyLines += ""
$bodyLines += $chatId
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
Write-Host "Bundle sent with banner"
} catch {
# Fallback to text
$textUri = "https://api.telegram.org/bot$token/sendMessage"
$textBody = @{ chat_id = $chatId; text = $caption } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri $textUri -Method Post -Body $textBody -ContentType "application/json" | Out-Null
Write-Host "Banner failed, sent as text"
}
} else {
$uri = "https://api.telegram.org/bot$token/sendMessage"
$body = @{ chat_id = $chatId; text = $caption } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" | Out-Null
Write-Host "Bundle sent as text (no banner found)"
}
# Save last message for debugging
$caption | Out-File "$ROOT\data\logs\bundle-run-log.last.txt" -Encoding UTF8
Write-Host "Done"