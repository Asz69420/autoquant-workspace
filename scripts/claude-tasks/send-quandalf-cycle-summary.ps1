param(
  [Parameter(Mandatory=$true)]
  [string]$TaskLabel,
  [string]$Summary,
  [string]$SourceFile,
  [int]$MaxChars = 320
)

$ErrorActionPreference = "Stop"
$ROOT = "C:\Users\Clamps\.openclaw\workspace"

function Convert-ToCompactText([string]$rawText, [int]$maxChars = 320) {
  if ([string]::IsNullOrWhiteSpace($rawText)) { return "" }

  $t = $rawText -replace '(?m)^\s{0,3}#{1,6}\s*', ''
  $t = $t -replace '(?m)^\s*>\s*', ''
  $t = $t -replace '(?m)^\s*[-*]\s+', ''
  $t = $t -replace '[*_`\[\]\|]', ' '
  $t = $t -replace '\s+', ' '
  $t = $t.Trim()

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
      $raw = Get-Content $SourceFile -Raw -ErrorAction SilentlyContinue
      if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $effectiveSummary = $raw.Substring(0, [Math]::Min(1600, $raw.Length))
      }
    }
  }

  $effectiveSummary = Convert-ToCompactText -rawText $effectiveSummary -maxChars $MaxChars
  if ([string]::IsNullOrWhiteSpace($effectiveSummary)) {
    $effectiveSummary = "Cycle completed."
  }

  $msg = "🧙‍♂️ Quandalf $TaskLabel: $effectiveSummary"

  powershell -ExecutionPolicy Bypass -File "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg | Out-Null
  Write-Host "Quandalf DM summary sent"
}
catch {
  Write-Host ("Quandalf DM summary failed: " + $_.Exception.Message)
}
