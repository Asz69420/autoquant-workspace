# Send a DM to Asz via Quandalf's Telegram bot
# Usage: powershell -File notify-asz.ps1 -Message "Your message here"
param(
  [Parameter(Mandatory=$true)]
  [string]$Message
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$envFile = "$ROOT\scripts\claude-bridge\.env"

if (-not (Test-Path $envFile)) {
  Write-Host "No .env file"
  exit 1
}

$token = $null
$chatId = $null

Get-Content $envFile | ForEach-Object {
  if ($_ -match '^CLAUDE_BRIDGE_BOT_TOKEN=(.*)$') {
    $token = $matches[1].Trim()
  }
  if ($_ -match '^CLAUDE_BRIDGE_USER_ID=(.*)$') {
    $chatId = $matches[1].Trim()
  }
}

if (-not $token -or -not $chatId) {
  Write-Host "Missing token or user ID"
  exit 1
}

function Convert-MarkupToHtml([string]$text) {
  if ([string]::IsNullOrWhiteSpace($text)) { return "" }

  $rawLines = $text -split "`r?`n"
  $outLines = New-Object System.Collections.Generic.List[string]

  foreach ($rawLine in $rawLines) {
    if ($rawLine -match '^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$') {
      continue
    }

    $line = [string]$rawLine
    $line = $line -replace '`', ''
    $line = [System.Net.WebUtility]::HtmlEncode($line)

    # Header conversion
    $line = $line -replace '^###\s+(.+)$', '<b>$1</b>'
    $line = $line -replace '^##\s+(.+)$', '<b>$1</b>'
    $line = $line -replace '^#\s+(.+)$', '<b>$1</b>'

    # Lightweight markdown support
    $line = $line -replace '\*\*(.+?)\*\*', '<b>$1</b>'
    $line = $line -replace '__(.+?)__', '<b>$1</b>'
    $line = $line -replace '(?<!\*)\*(.+?)(?<!\*)\*', '<i>$1</i>'

    # Normalize bullets for cleaner Telegram rendering
    $line = $line -replace '^\s*[-*]\s+', '• '

    [void]$outLines.Add($line)
  }

  return ($outLines -join "`n")
}

$url = "https://api.telegram.org/bot$token/sendMessage"
$renderedMessage = Convert-MarkupToHtml -text $Message
$body = @{
  chat_id = $chatId
  text = $renderedMessage
  parse_mode = "HTML"
} | ConvertTo-Json -Compress
$body = $body -replace '\\u003c', '<' -replace '\\u003e', '>'

try {
  $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
  $response = Invoke-RestMethod -Uri $url -Method Post -Body $bodyBytes -ContentType "application/json; charset=utf-8"

  if ($null -eq $response -or $response.ok -ne $true) {
    throw "Telegram API returned non-OK response."
  }

  Write-Output $response
  Write-Host "DM sent to Asz"
}
catch {
  throw "Failed to send DM: $($_.Exception.Message)"
}
