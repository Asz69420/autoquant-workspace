param()

$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location -LiteralPath $ROOT
$scriptStart = Get-Date

function Escape-Html {
  param([string]$Text)
  if ($null -eq $Text) { return '' }
  $escaped = [string]$Text
  $escaped = $escaped -replace '&', '&amp;'
  $escaped = $escaped -replace '<', '&lt;'
  $escaped = $escaped -replace '>', '&gt;'
  return $escaped
}

# 1) Run digest worker
$workerOut = & python "$ROOT\scripts\pipeline\research_digest_worker.py" 2>&1
if ($LASTEXITCODE -ne 0) {
  throw ("research_digest_worker.py failed: " + [string]($workerOut -join ' '))
}

$workerText = [string]($workerOut -join "`n")
$workerJson = $null
try {
  $workerJson = $workerText | ConvertFrom-Json
} catch {
  throw ("Unable to parse research digest output: " + $workerText)
}

$scanned = 0
$digestEntries = 0
$added = 0
if ($workerJson) {
  if ($workerJson.PSObject.Properties.Name -contains 'total_cards_scanned') { $scanned = [int]$workerJson.total_cards_scanned }
  if ($workerJson.PSObject.Properties.Name -contains 'entries_in_digest') { $digestEntries = [int]$workerJson.entries_in_digest }
  if ($workerJson.PSObject.Properties.Name -contains 'new_entries') { $added = [int]$workerJson.new_entries }
}

# 2) Resolve Telegram log token/channel from .env (Logron transport)
$wsEnv = "$ROOT\.env"
if (-not (Test-Path -LiteralPath $wsEnv)) { throw 'Missing workspace .env' }

$token = $null
$logBotToken = $null
$logChannel = $null
Get-Content -LiteralPath $wsEnv -Encoding UTF8 | ForEach-Object {
  if ($_ -match '^TELEGRAM_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  if ($_ -match '^TELEGRAM_LOG_BOT_TOKEN=(.*)$') { $logBotToken = $matches[1].Trim() }
  if ($_ -match '^TELEGRAM_LOG_CHAT_ID=(.*)$') { $logChannel = $matches[1].Trim() }
}
if ([string]::IsNullOrWhiteSpace($logChannel)) { throw 'Missing TELEGRAM_LOG_CHAT_ID in .env' }
$telegramSendToken = if (-not [string]::IsNullOrWhiteSpace($logBotToken)) { $logBotToken } else { $token }
if ([string]::IsNullOrWhiteSpace($telegramSendToken)) { throw 'Missing Telegram token in .env' }

# 3) Build Quandalf-styled digest caption (no file path line)
$lines = @()
$activityDivider = ([char]0x25CB) + (([string][char]0x2500) * 3) + 'activity' + (([string][char]0x2500) * 21)
$dur = New-TimeSpan -Start $scriptStart -End (Get-Date)
$durLabel = (([int]$dur.TotalMinutes).ToString() + 'm ' + $dur.Seconds.ToString('00') + 's')
$emojiDigest = [System.Char]::ConvertFromUtf32(0x1F4E5)
$iconOk = [char]0x2705
$lines += ($emojiDigest + " Digest")
$lines += ("Status: " + $iconOk + " | Duration: " + $durLabel)
$lines += $activityDivider
$lines += "Scanned: $scanned"
$lines += "Digest: $digestEntries"
$lines += "Added: $added"
$messageBody = ($lines -join "`n").TrimEnd()

$escapedBody = Escape-Html -Text $messageBody
if ($escapedBody.Length -gt 985) { $escapedBody = $escapedBody.Substring(0, 982) + '...' }
$caption = '<pre>' + $escapedBody + '</pre>'

# 4) Select Quandalf banner
$bannerPath = $null
$bannerDir = "$ROOT\assets\banners"
if (Test-Path -LiteralPath $bannerDir) {
  $bannerFiles = Get-ChildItem -LiteralPath $bannerDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^quandalf_banner\.' }
  if ($bannerFiles -and $bannerFiles.Count -gt 0) { $bannerPath = $bannerFiles[0].FullName }
}

if ([string]::IsNullOrWhiteSpace($bannerPath)) {
  throw 'Missing Quandalf banner in assets/banners (expected quandalf_banner.*)'
}

# 5) Send photo + caption to log channel (Logron bot token)
$uri = "https://api.telegram.org/bot$telegramSendToken/sendPhoto"
$boundary = [System.Guid]::NewGuid().ToString()
$parts = @()
$parts += "--$boundary`r`nContent-Disposition: form-data; name=`"chat_id`"`r`n`r`n$logChannel"
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

Invoke-RestMethod -Uri $uri -Method Post -Body $fullBody -ContentType "multipart/form-data; boundary=$boundary" | Out-Null

Write-Output ("OK scanned=" + $scanned + " digest=" + $digestEntries + " added=" + $added)
