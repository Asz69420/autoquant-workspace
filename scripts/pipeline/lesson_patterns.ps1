# Scan lessons.ndjson for recurring patterns. Non-blocking, no LLM.
# Run periodically (e.g. daily with Doctrine task).
$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$logPath = "$ROOT\data\logs\lessons.ndjson"

if (-not (Test-Path $logPath)) {
  Write-Output "No lessons yet"
  exit 0
}

$lines = Get-Content $logPath -Encoding UTF8
$errors = @{}

foreach ($line in $lines) {
  try {
    $entry = $line | ConvertFrom-Json
    if ($entry.type -in @("error", "violation")) {
      $key = "$($entry.agent):$($entry.detail)"
      if ($key.Length -gt 80) { $key = $key.Substring(0, 80) }
      $errors[$key] = ($errors[$key] ?? 0) + 1
    }
  } catch {
    continue
  }
}

$patterns = $errors.GetEnumerator() | Where-Object { $_.Value -ge 3 } | Sort-Object Value -Descending

if ($patterns.Count -gt 0) {
  Write-Output "RECURRING PATTERNS FOUND:"
  foreach ($p in $patterns) {
    Write-Output " $($p.Key): $($p.Value)x"
  }

  # DM Asz only if new patterns emerge
  $msg = "📊 Lesson Patterns:`n"
  foreach ($p in $patterns) {
    $msg += " $($p.Key): $($p.Value)x`n"
  }
  powershell -File "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $msg
} else {
  Write-Output "No recurring patterns yet"
}
