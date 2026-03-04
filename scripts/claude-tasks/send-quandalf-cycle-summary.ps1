param(
  [Parameter(Mandatory=$true)]
  [string]$TaskLabel,
  [string]$Summary,
  [string]$SourceFile,
  [int]$MaxChars = 3500
)

$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$bridgeEnv = "$ROOT\scripts\claude-bridge\.env"

function Convert-ToCompactText([string]$rawText, [int]$maxChars = 3500) {
  if ([string]::IsNullOrWhiteSpace($rawText)) { return "" }

  $t = $rawText.Trim()

  if ([string]::IsNullOrWhiteSpace($t)) { return "" }

  if ($t.Length -gt $maxChars) {
    return $t.Substring(0, $maxChars - 3) + "..."
  }
  return $t
}

function Get-TextSha256([string]$text) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$text)
    $hashBytes = $sha.ComputeHash($bytes)
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
  }
  finally {
    $sha.Dispose()
  }
}

function Normalize-JournalEntry([string]$text) {
  if ([string]::IsNullOrWhiteSpace($text)) { return "" }

  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($line in ($text -split "`r?`n")) {
    [void]$lines.Add([string]$line)
  }

  while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[0])) {
    $lines.RemoveAt(0)
  }

  while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
    $lines.RemoveAt($lines.Count - 1)
  }

  while ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -match '^\s*---\s*$') {
    $lines.RemoveAt($lines.Count - 1)
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
      $lines.RemoveAt($lines.Count - 1)
    }
  }

  $normalized = ($lines -join "`n")

  # Remove machine-directive JSON blocks from DM journal view
  $normalized = [System.Text.RegularExpressions.Regex]::Replace(
    $normalized,
    '(?is)(?:^|\n)\s*(?:---\s*)?machine\s+directives\b.*?(?=(?:\n##\s+|\n###\s+|\z))',
    "`n"
  )

  # Collapse excessive blank lines after removal
  $normalized = [System.Text.RegularExpressions.Regex]::Replace($normalized, '(?m)^(\s*\r?\n){3,}', "`n`n")

  return $normalized.Trim()
}

function Build-JournalDigest([string]$entryText, [int]$maxChars = 1400) {
  $entry = Normalize-JournalEntry -text $entryText
  if ([string]::IsNullOrWhiteSpace($entry)) { return "" }

  $title = ""
  $mTitle = [System.Text.RegularExpressions.Regex]::Match($entry, '(?m)^##\s+Entry\b.*$')
  if ($mTitle.Success) { $title = $mTitle.Value.Trim() }

  $wanted = @(
    'Results',
    'Key Insights?',
    'What I.?m Testing Next',
    'Suggestions for Asz(?:\s*\(if any\))?',
    'What I learned this cycle',
    'What changed in my thinking',
    'What I.?m testing next'
  )

  $sections = @()
  foreach ($pat in $wanted) {
    $rx = '(?ims)^###\s*(' + $pat + ')\s*\r?\n(.*?)(?=^###\s+|\z)'
    $m = [System.Text.RegularExpressions.Regex]::Match($entry, $rx)
    if ($m.Success) {
      $h = ([string]$m.Groups[1].Value -replace '\s+', ' ').Trim()
      $b = ([string]$m.Groups[2].Value -replace '\s+', ' ').Trim()
      if ($b.Length -gt 320) { $b = $b.Substring(0, 320).TrimEnd() + '…' }
      $sections += ("### " + $h + "`n" + $b)
    }
  }

  if ($sections.Count -eq 0) {
    return Convert-ToCompactText -rawText $entry -maxChars $maxChars
  }

  $out = @()
  if (-not [string]::IsNullOrWhiteSpace($title)) { $out += $title }
  $out += $sections
  $text = ($out -join "`n`n").Trim()
  return Convert-ToCompactText -rawText $text -maxChars $maxChars
}

function Get-BridgeVar([string]$key) {
  if (-not (Test-Path $bridgeEnv)) { return "" }

  foreach ($line in (Get-Content -Path $bridgeEnv -Encoding UTF8 -ErrorAction SilentlyContinue)) {
    if ($line -match ('^' + [regex]::Escape($key) + '=(.*)$')) {
      return [string]$matches[1].Trim()
    }
  }

  return ""
}

function Send-QuandalfBannerPhoto([string]$captionText) {
  $token = Get-BridgeVar -key 'CLAUDE_BRIDGE_BOT_TOKEN'
  $chatId = Get-BridgeVar -key 'CLAUDE_BRIDGE_USER_ID'
  if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chatId)) { return }

  $bannerPath = ""
  $bannerDir = "$ROOT\assets\banners"
  if (Test-Path $bannerDir) {
    $candidate = Get-ChildItem -Path $bannerDir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^quandalf_banner\.' } | Select-Object -First 1
    if ($candidate) { $bannerPath = [string]$candidate.FullName }
  }

  if ([string]::IsNullOrWhiteSpace($bannerPath) -or -not (Test-Path $bannerPath)) { return }

  $caption = [string]$captionText
  if ([string]::IsNullOrWhiteSpace($caption)) { $caption = 'Quandalf journal cycle' }
  if ($caption.Length -gt 120) { $caption = $caption.Substring(0, 120) }

  $env:QB_TOKEN = $token
  $env:QB_CHAT = $chatId
  $env:QB_CAPTION = $caption
  $env:QB_PHOTO = $bannerPath

  $py = @'
import os
import requests

token = (os.getenv("QB_TOKEN") or "").strip()
chat = (os.getenv("QB_CHAT") or "").strip()
caption = (os.getenv("QB_CAPTION") or "").strip()
photo = (os.getenv("QB_PHOTO") or "").strip()

if token and chat and photo:
    with open(photo, "rb") as fh:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat, "caption": caption},
            files={"photo": fh},
            timeout=60,
        )
        r.raise_for_status()
'@

  $null = $py | python -
}

try {
  $effectiveSummary = $Summary
  $isJournalEntry = $false

  if ([string]::IsNullOrWhiteSpace($effectiveSummary) -and -not [string]::IsNullOrWhiteSpace($SourceFile)) {
    if (Test-Path $SourceFile) {
      $raw = Get-Content -Path $SourceFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
      if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $journalMatches = [System.Text.RegularExpressions.Regex]::Matches($raw, '(?ms)^## Entry\b.*?(?=^## Entry\b|\z)')
        if ($journalMatches.Count -gt 0) {
          $effectiveSummary = Normalize-JournalEntry -text $journalMatches[$journalMatches.Count - 1].Value
          $isJournalEntry = $true
        }
        else {
          $effectiveSummary = Normalize-JournalEntry -text $raw
        }
      }
    }
  }

  if (-not $isJournalEntry) {
    $effectiveSummary = Convert-ToCompactText -rawText $effectiveSummary -maxChars $MaxChars
  }

  if ([string]::IsNullOrWhiteSpace($effectiveSummary)) {
    $effectiveSummary = "Cycle completed."
  }

  $msg = "Quandalf ${TaskLabel}:`n$effectiveSummary"

  if ($isJournalEntry) {
    $stateDir = "$ROOT\data\logs\claude-tasks"
    $statePath = "$stateDir\last-journal-dm.sha256"
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

    $currentHash = Get-TextSha256 -text $effectiveSummary
    $lastHash = ""
    if (Test-Path $statePath) {
      $lastHash = [string](Get-Content -Path $statePath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue)
      $lastHash = $lastHash.Trim()
    }

    if (-not [string]::IsNullOrWhiteSpace($lastHash) -and $lastHash -eq $currentHash) {
      Write-Host "Quandalf DM summary skipped (duplicate journal entry)"
      return
    }

    & "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg
    Send-QuandalfBannerPhoto -captionText "Quandalf journal cycle"
    Set-Content -Path $statePath -Value $currentHash -Encoding UTF8
    Write-Host "Quandalf DM summary sent"
    return
  }

  & "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg

  Write-Host "Quandalf DM summary sent"
}
catch {
  throw ("Quandalf DM summary failed: " + $_.Exception.Message)
}
