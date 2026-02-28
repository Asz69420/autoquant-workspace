param(
  [switch]$QuietMode
)

$ErrorActionPreference = 'Stop'

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$envFile = Join-Path $ROOT 'scripts\claude-bridge\.env'
$outbox = Join-Path $ROOT 'data\logs\outbox'
$cutoff = (Get-Date).AddMinutes(-15)
$ts = Get-Date -Format 'h:mm tt'

if (-not (Test-Path -LiteralPath $envFile)) { exit 0 }
if (-not (Test-Path -LiteralPath $outbox)) { exit 0 }

$events = @()
Get-ChildItem -Path (Join-Path $outbox '*.json') -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -ge $cutoff } |
  ForEach-Object {
    try {
      $ev = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
      if ($null -ne $ev) {
        $ev | Add-Member -NotePropertyName '__file_time' -NotePropertyValue $_.LastWriteTime -Force
        $events += $ev
      }
    } catch {}
  }

if ($events.Count -eq 0) { exit 0 }

function Get-EventTime([object]$ev) {
  try {
    if ($ev.ts_iso) { return ([DateTimeOffset]::Parse([string]$ev.ts_iso)).UtcDateTime }
  } catch {}
  try {
    if ($ev.__file_time) { return ([DateTime]$ev.__file_time).ToUniversalTime() }
  } catch {}
  return [DateTime]::MinValue
}

$sorted = @($events | Sort-Object { Get-EventTime $_ })

# Dedupe by run_id + reason_code + status_word (keep earliest in sorted order)
$seen = New-Object 'System.Collections.Generic.HashSet[string]'
$deduped = @()
foreach ($ev in $sorted) {
  $kRun = if ($ev.run_id) { [string]$ev.run_id } else { '' }
  $kReason = if ($ev.reason_code) { [string]$ev.reason_code } else { '' }
  $kStatus = if ($ev.status_word) { [string]$ev.status_word } else { '' }
  $key = "$kRun|$kReason|$kStatus"
  if ($seen.Add($key)) { $deduped += $ev }
}

if ($deduped.Count -eq 0) { exit 0 }

$hasErrors = (@($deduped | Where-Object { [string]$_.status_word -eq 'FAIL' }).Count -gt 0)
$hasWarns = (@($deduped | Where-Object { [string]$_.status_word -eq 'WARN' }).Count -gt 0)
$hasPromo = (@($deduped | Where-Object {
  ([string]$_.action -match 'PROMOT') -and ([string]$_.summary -notmatch 'SKIPPED')
}).Count -gt 0)

$status = 'IDLE'
if ($hasErrors) { $status = 'ERRORS' }
elseif ($hasPromo) { $status = 'PRODUCED' }
elseif ($hasWarns) { $status = 'WARN' }

if ($QuietMode -and $status -eq 'IDLE') { exit 0 }

$emoji = @{
  'IDLE' = '🔷'
  'PRODUCED' = '🟢'
  'WARN' = '🟡'
  'ERRORS' = '🔴'
}[$status]

$agentIcons = @{
  'Backtester' = '📊'
  'Librarian'  = '📚'
  'Promotion'  = '🚀'
  'Refinement' = '🔁'
  'Lab'        = '🧪'
  'oQ'         = '📋'
  'Strategist' = '🧠'
  'Reader'     = '📖'
  'Grabber'    = '📥'
  'Quandalf'   = '🟣'
  'Frodex'     = '🔷'
}

$grouped = $deduped | Group-Object agent | Sort-Object Name

$lines = @()
$lines += "$emoji oQ LOG | $ts | $($deduped.Count) events | $status"
$lines += ''

foreach ($group in $grouped) {
  $agentName = [string]$group.Name
  $icon = $agentIcons[$agentName]
  if (-not $icon) { $icon = '▫️' }

  $lines += "$icon $agentName"

  foreach ($ev in ($group.Group | Sort-Object { Get-EventTime $_ })) {
    $sum = [string]$ev.summary
    if (-not [string]::IsNullOrWhiteSpace($sum)) {
      $sum = $sum -replace '^[A-Za-z]+:\s*', ''
    }
    $sw = @{
      'OK'   = '✅'
      'WARN' = '⚠️'
      'FAIL' = '❌'
    }[[string]$ev.status_word]
    if (-not $sw) { $sw = '▪️' }
    $lines += " $sw $sum"
  }

  $lines += ''
}

$message = ($lines -join "`n").TrimEnd()

# Telegram 4096-char guard
$maxLen = 4096
$suffix = '... truncated'
if ($message.Length -gt $maxLen) {
  $keep = $maxLen - $suffix.Length
  if ($keep -lt 0) { $keep = 0 }
  $message = $message.Substring(0, $keep) + $suffix
}

$token = $null
$chatId = $null
Get-Content -LiteralPath $envFile | ForEach-Object {
  if ($_ -match '^CLAUDE_BRIDGE_BOT_TOKEN=(.*)$') { $token = $matches[1].Trim() }
  if ($_ -match '^CLAUDE_BRIDGE_USER_ID=(.*)$') { $chatId = $matches[1].Trim() }
}

if (-not $token -or -not $chatId) { exit 0 }

Add-Type -AssemblyName System.Web
$html = '<pre>' + [System.Web.HttpUtility]::HtmlEncode($message) + '</pre>'
$body = @{ chat_id = $chatId; text = $html; parse_mode = 'HTML' } | ConvertTo-Json -Compress

try {
  Invoke-RestMethod -Uri ("https://api.telegram.org/bot$token/sendMessage") -Method Post -Body $body -ContentType 'application/json' | Out-Null
} catch {
  Write-Host "Send failed: $_"
}
