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

$url = "https://api.telegram.org/bot$token/sendMessage"
$body = @{
  chat_id = $chatId
  text = $Message
  parse_mode = "Markdown"
} | ConvertTo-Json -Compress

try {
  Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json" | Out-Null
  Write-Host "DM sent to Asz"
} catch {
  Write-Host "Failed to send DM: $_"
}
