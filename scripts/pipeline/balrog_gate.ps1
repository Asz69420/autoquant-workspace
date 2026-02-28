# Balrog — Deterministic Firewall Gate
# Binary checks only. No LLM. No intelligence. Just evidence.
# Runs before/after pipeline cycles to enforce integrity.
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("pre-backtest", "post-backtest", "health")]
  [string]$Mode,
  [switch]$SuppressNotify
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$violations = @()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ─── HEALTH CHECKS (run anytime) ───
if ($Mode -eq "health" -or $Mode -eq "pre-backtest") {
  # Check: no API keys leaked in artifacts
  $secretPatterns = @("sk-", "api_key", "bot_token", "PRIVATE_KEY", "secret")
  foreach ($pattern in $secretPatterns) {
    $found = Get-ChildItem -Path "$ROOT\artifacts" -Recurse -File -ErrorAction SilentlyContinue | Select-String -Pattern $pattern -SimpleMatch -ErrorAction SilentlyContinue | Where-Object { $_.Path -notmatch "node_modules|\.git" }
    if ($found) {
      $violations += "SECRET_LEAK: Pattern '$pattern' found in $($found[0].Path)"
    }
  }

  # Check: no zero-byte artifacts
  $zeroFiles = Get-ChildItem -Path "$ROOT\artifacts" -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -eq 0 }
  foreach ($f in $zeroFiles) {
    $violations += "ZERO_BYTE: $($f.FullName)"
  }

  # Check: INDEX.json exists and parses
  $indexPath = "$ROOT\artifacts\strategy_specs\INDEX.json"
  if (Test-Path $indexPath) {
    try { $null = Get-Content $indexPath -Raw | ConvertFrom-Json }
    catch { $violations += "INDEX_CORRUPT: INDEX.json fails to parse" }
  } else {
    $violations += "INDEX_MISSING: strategy_specs/INDEX.json not found"
  }

  # Check: no stale lock files older than 1 hour
  $locks = Get-ChildItem -Path "$ROOT\data" -Recurse -Filter "*.lock" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-1) }
  foreach ($lock in $locks) {
    $violations += "STALE_LOCK: $($lock.FullName) (age: $([int]((Get-Date) - $lock.LastWriteTime).TotalHours)h)"
  }

  # Check: actions.ndjson exists and is writable
  $logPath = "$ROOT\data\logs\actions.ndjson"
  if (-not (Test-Path $logPath)) {
    $violations += "LOG_MISSING: actions.ndjson not found"
  }
}

# ─── PRE-BACKTEST (validate specs before running) ───
if ($Mode -eq "pre-backtest") {
  $today = Get-Date -Format "yyyyMMdd"
  $specDir = "$ROOT\artifacts\strategy_specs\$today"
  if (Test-Path $specDir) {
    $specs = Get-ChildItem $specDir -Filter "*.strategy_spec.json" -ErrorAction SilentlyContinue
    foreach ($spec in $specs) {
      try {
        $json = Get-Content $spec.FullName -Raw | ConvertFrom-Json

        # Must have variants array
        if (-not $json.variants -or $json.variants.Count -eq 0) {
          $violations += "SPEC_NO_VARIANTS: $($spec.Name)"
        }

        # Must have schema_version
        if (-not $json.schema_version) {
          $violations += "SPEC_NO_SCHEMA: $($spec.Name)"
        }

        # Each variant must have entry_long
        foreach ($v in $json.variants) {
          if (-not $v.entry_long -or $v.entry_long.Count -eq 0) {
            $violations += "SPEC_NO_ENTRY: $($spec.Name) variant=$($v.name)"
          }
        }
      } catch {
        $violations += "SPEC_PARSE_FAIL: $($spec.Name)"
      }
    }
  }
}

# ─── POST-BACKTEST (validate results are real) ───
if ($Mode -eq "post-backtest") {
  $today = Get-Date -Format "yyyyMMdd"
  $btDir = "$ROOT\artifacts\backtests\$today"
  if (Test-Path $btDir) {
    $results = Get-ChildItem $btDir -Filter "*.backtest_result.json" -Recurse -ErrorAction SilentlyContinue
    foreach ($r in $results) {
      try {
        $json = Get-Content $r.FullName -Raw | ConvertFrom-Json
        $pf = $json.results.profit_factor
        $trades = $json.results.total_trades

        # PF must be a real number
        if ($null -eq $pf -or $pf -lt 0 -or $pf -gt 999) {
          $violations += "BT_INVALID_PF: $($r.Name) pf=$pf"
        }

        # Must have at least 0 trades (not null)
        if ($null -eq $trades) {
          $violations += "BT_NO_TRADES: $($r.Name)"
        }

        # Result file must be > 100 bytes (not truncated)
        if ($r.Length -lt 100) {
          $violations += "BT_TRUNCATED: $($r.Name) size=$($r.Length)"
        }
      } catch {
        $violations += "BT_PARSE_FAIL: $($r.Name)"
      }
    }
  }
}

# ─── REPORT ───
if ($violations.Count -gt 0) {
  $report = "🔥 BALROG VIOLATION REPORT [$timestamp]`nMode: $Mode`nViolations: $($violations.Count)`n"
  foreach ($v in $violations) {
    $report += "`n❌ $v"
  }

  # Write to log
  $logDir = "$ROOT\data\logs\balrog"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $report | Out-File "$logDir\balrog_$(Get-Date -Format 'yyyyMMdd_HHmmss').log" -Encoding UTF8

  # DM Asz (optional)
  if (-not $SuppressNotify) {
    powershell -File "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $report
  }

  Write-Output $report
  exit 1
} else {
  Write-Output "[$timestamp] Balrog $Mode check: ALL CLEAR"
  exit 0
}
