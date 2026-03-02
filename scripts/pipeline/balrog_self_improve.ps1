# Balrog Self-Improvement — tracks recurring violations and escalates patterns
# Reads balrog logs, counts recurring violations, writes to doctrine if pattern found
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$logDir = "$ROOT\data\logs\balrog"
if (-not (Test-Path $logDir)) {
  Write-Output "No Balrog logs yet"
  exit 0
}

$logs = Get-ChildItem $logDir -Filter "*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 50
$patterns = @{}

foreach ($log in $logs) {
  $content = Get-Content $log.FullName -ErrorAction SilentlyContinue
  foreach ($line in $content) {
    if ($line -match "^. (.+?):\s") {
      $type = $matches[1]
      $patterns[$type] = ($patterns[$type] ?? 0) + 1
    }
  }
}

$recurring = $patterns.GetEnumerator() | Where-Object { $_.Value -ge 3 } | Sort-Object Value -Descending

if ($recurring.Count -gt 0) {
  $report = "🔥 BALROG PATTERN ALERT — Recurring violations:`n"
  foreach ($r in $recurring) {
    $report += "`n $($r.Key): $($r.Value)x in last 50 checks"
  }

  # Append to doctrine as a warning
  $doctrinePath = "$ROOT\docs\DOCTRINE\analyser-doctrine.md"
  if (Test-Path $doctrinePath) {
    $existing = Get-Content $doctrinePath -Raw
    if ($existing -notmatch "BALROG_PATTERN") {
      Add-Content $doctrinePath "`n`n## BALROG_PATTERN_ALERTS`n$report"
    }
  }

  # Telegram notifications temporarily disabled until Balrog has its own bot token.
  # powershell -File "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $report

  Write-Output $report
} else {
  Write-Output "No recurring patterns found"
}
