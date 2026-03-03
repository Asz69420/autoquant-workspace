# Send a DM to Asz via Quandalf's Telegram bot
# Usage: powershell -File notify-asz.ps1 -Message "Your message here"
param(
  [Parameter(Mandatory=$true)]
  [string]$Message,
  [switch]$PlainText
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

    # Markdown table row -> readable bullet row
    if ($line -match '^\s*\|.*\|\s*$') {
      $cells = @($line.Trim() -split '\|' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
      if ($cells.Count -gt 0) {
        $line = '• ' + ($cells -join '  |  ')
      }
    }

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

function Split-MessageChunks([string]$text, [int]$maxChars = 3500) {
  $chunks = New-Object System.Collections.Generic.List[string]
  if ([string]::IsNullOrEmpty($text)) {
    [void]$chunks.Add("")
    return $chunks
  }

  $lines = $text -split "`r?`n"
  $buffer = ""

  foreach ($line in $lines) {
    $lineText = [string]$line

    if ($lineText.Length -gt $maxChars) {
      if ($buffer.Length -gt 0) {
        [void]$chunks.Add($buffer.TrimEnd("`r","`n"))
        $buffer = ""
      }

      $start = 0
      while ($start -lt $lineText.Length) {
        $len = [Math]::Min($maxChars, $lineText.Length - $start)
        [void]$chunks.Add($lineText.Substring($start, $len))
        $start += $len
      }
      continue
    }

    if ($buffer.Length -eq 0) {
      $buffer = $lineText
      continue
    }

    $candidate = $buffer + "`n" + $lineText
    if ($candidate.Length -le $maxChars) {
      $buffer = $candidate
    }
    else {
      [void]$chunks.Add($buffer.TrimEnd("`r","`n"))
      $buffer = $lineText
    }
  }

  if ($buffer.Length -gt 0) {
    [void]$chunks.Add($buffer.TrimEnd("`r","`n"))
  }

  if ($chunks.Count -eq 0) {
    [void]$chunks.Add("")
  }

  return $chunks
}

function Send-TelegramMessage([string]$url, [string]$chatId, [string]$text, [bool]$useHtml = $true) {
  $bodyObj = @{
    chat_id = $chatId
    text = $text
  }

  if ($useHtml) {
    $bodyObj.parse_mode = "HTML"
  }

  $body = $bodyObj | ConvertTo-Json -Compress
  $body = $body -replace '\\u003c', '<' -replace '\\u003e', '>'

  $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
  $response = Invoke-RestMethod -Uri $url -Method Post -Body $bodyBytes -ContentType "application/json; charset=utf-8"

  if ($null -eq $response -or $response.ok -ne $true) {
    throw "Telegram API returned non-OK response."
  }

  return $response
}

$url = "https://api.telegram.org/bot$token/sendMessage"
$chunks = @(Split-MessageChunks -text $Message -maxChars 3500)
$total = $chunks.Count
$responses = New-Object System.Collections.Generic.List[object]

try {
  for ($i = 0; $i -lt $total; $i++) {
    $chunkText = $chunks[$i]
    if ($total -gt 1) {
      $prefix = "[Part $($i + 1)/$total]`n"
      $chunkText = $prefix + $chunkText
    }

    $outText = $chunkText
    $useHtml = -not $PlainText
    if ($useHtml) {
      $outText = Convert-MarkupToHtml -text $chunkText
    }

    $response = Send-TelegramMessage -url $url -chatId $chatId -text $outText -useHtml $useHtml
    [void]$responses.Add($response)
  }

  $responses | Write-Output
  Write-Host "DM sent to Asz"
}
catch {
  throw "Failed to send DM: $($_.Exception.Message)"
}
