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

  $escaped = [System.Security.SecurityElement]::Escape($text)
  $escaped = $escaped -replace '`', ''

  # Bold markers
  $escaped = $escaped -replace '\*\*(.+?)\*\*', '<b>$1</b>'
  $escaped = $escaped -replace '__(.+?)__', '<b>$1</b>'

  # Italic markers
  $escaped = $escaped -replace '(?<!\*)\*(.+?)(?<!\*)\*', '<i>$1</i>'
  $escaped = $escaped -replace '(?<!_)_(.+?)(?<!_)_', '<i>$1</i>'

  return $escaped
}

$url = "https://api.telegram.org/bot$token/sendMessage"
$renderedMessage = Convert-MarkupToHtml -text $Message
$body = @{
  chat_id = $chatId
  text = $renderedMessage
  parse_mode = "HTML"
} | ConvertTo-Json -Compress

try {
  $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
  Write-Output $response
  Write-Host "DM sent to Asz"
} catch {
  Write-Host "Failed to send DM: $_"
}
