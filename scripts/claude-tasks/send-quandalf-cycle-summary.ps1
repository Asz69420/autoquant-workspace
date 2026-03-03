param(
  [Parameter(Mandatory=$true)]
  [string]$TaskLabel,
  [string]$Summary,
  [string]$SourceFile,
  [int]$MaxChars = 3500
)

$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"

function Convert-ToCompactText([string]$rawText, [int]$maxChars = 3500) {
  if ([string]::IsNullOrWhiteSpace($rawText)) { return "" }

  $t = $rawText.Trim()

  if ([string]::IsNullOrWhiteSpace($t)) { return "" }

  if ($t.Length -gt $maxChars) {
    return $t.Substring(0, $maxChars - 3) + "..."
  }
  return $t
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

  return ($lines -join "`n")
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
    & "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg -PlainText
  }
  else {
    & "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg
  }

  Write-Host "Quandalf DM summary sent"
}
catch {
  throw ("Quandalf DM summary failed: " + $_.Exception.Message)
}
