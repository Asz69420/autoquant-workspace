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

try {
  $effectiveSummary = $Summary

  if ([string]::IsNullOrWhiteSpace($effectiveSummary) -and -not [string]::IsNullOrWhiteSpace($SourceFile)) {
    if (Test-Path $SourceFile) {
      $raw = Get-Content -Path $SourceFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
      if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $entrySections = @($raw -split '(?m)^## Entry\b')
        $lastSection = $null
        for ($i = $entrySections.Count - 1; $i -ge 0; $i--) {
          $candidate = [string]$entrySections[$i]
          if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $lastSection = $candidate.Trim()
            break
          }
        }

        if (-not [string]::IsNullOrWhiteSpace($lastSection)) {
          $effectiveSummary = $lastSection
        } else {
          $effectiveSummary = $raw
        }
      }
    }
  }

  $effectiveSummary = Convert-ToCompactText -rawText $effectiveSummary -maxChars $MaxChars
  if ([string]::IsNullOrWhiteSpace($effectiveSummary)) {
    $effectiveSummary = "Cycle completed."
  }

  $msg = "Quandalf ${TaskLabel}:`n$effectiveSummary"

  & "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg
  Write-Host "Quandalf DM summary sent"
}
catch {
  Write-Host ("Quandalf DM summary failed: " + $_.Exception.Message)
}
