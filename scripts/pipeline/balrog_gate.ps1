# Balrog - Deterministic Firewall Gate
# Binary checks only. No LLM. No intelligence. Just evidence.
# Runs before/after pipeline cycles to enforce integrity.
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("pre-backtest", "post-backtest", "health")]
  [string]$Mode,

  [Parameter(Mandatory=$false)]
  [string]$SpecPath = ""
)

$ROOT = "C:\Users\Clamps\.openclaw\workspace"
Set-Location $ROOT

$violations = @()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Test-IgnoredTempArtifactFile([System.IO.FileInfo]$File) {
  if ($null -eq $File) { return $false }

  $path = [string]$File.FullName
  $name = [string]$File.Name

  if ($path -match '(?i)[\\/]artifacts[\\/]tmp([\\/]|$)') { return $true }
  if ($name -match '(?i)^tmp.*\.tmp$') { return $true }
  if ($name -match '(?i)^tmp_.*\.(txt|json)$') { return $true }

  return $false
}

# --- HEALTH CHECKS (run anytime) ---
if ($Mode -eq "health" -or $Mode -eq "pre-backtest") {
  $artifactFiles = Get-ChildItem -Path "$ROOT\artifacts" -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.FullName -notmatch '(?i)node_modules|\.git' -and
      -not (Test-IgnoredTempArtifactFile $_)
    }

  # Check: no API keys leaked in artifacts (tight patterns only)
  $secretChecks = @(
    @{ Name = 'OPENAI_STYLE_KEY'; Pattern = '(?i)\bsk-[A-Za-z0-9]{20,}\b' },
    @{ Name = 'API_KEY_ASSIGNMENT'; Pattern = '(?i)\bapi[_-]?key\b\s*[:=]\s*["'']?[A-Za-z0-9_\-]{16,}' },
    @{ Name = 'TOKEN_ASSIGNMENT'; Pattern = '(?i)\b(?:token|bot[_-]?token)\b\s*[:=]\s*["'']?[A-Za-z0-9_\-]{16,}' },
    @{ Name = 'PRIVATE_KEY_BLOCK'; Pattern = '(?i)-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----' }
  )

  foreach ($check in $secretChecks) {
    $found = $artifactFiles | Select-String -Pattern $check.Pattern -ErrorAction SilentlyContinue
    if ($found) {
      $violations += "SECRET_LEAK: Pattern '$($check.Name)' found in $($found[0].Path)"
    }
  }

  # Check: no zero-byte artifacts (excluding known temp noise)
  $zeroFiles = $artifactFiles | Where-Object { $_.Length -eq 0 }
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

  # Check: forward champions config validates
  $championsPath = "$ROOT\docs\shared\CHAMPIONS.json"
  if (Test-Path $championsPath) {
    $validateOut = & python "$ROOT\scripts\forward\validate_champions.py" --file "$championsPath" 2>&1
    if ($LASTEXITCODE -ne 0) {
      $violations += "CHAMPIONS_INVALID: $([string]($validateOut -join ' '))"
    }
  }
}

# --- PRE-BACKTEST (validate specs before running) ---
if ($Mode -eq "pre-backtest") {
  $specs = @()

  if (-not [string]::IsNullOrWhiteSpace($SpecPath) -and (Test-Path -LiteralPath $SpecPath)) {
    $specs = @(Get-Item -LiteralPath $SpecPath -ErrorAction SilentlyContinue)
  } else {
    $today = Get-Date -Format "yyyyMMdd"
    $specDir = "$ROOT\artifacts\strategy_specs\$today"
    if (Test-Path $specDir) {
      $specs = @(Get-ChildItem $specDir -Filter "*.strategy_spec.json" -ErrorAction SilentlyContinue)
    }
  }

  if ($specs.Count -gt 0) {
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

# --- POST-BACKTEST (validate results are real) ---
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

# --- REPORT ---
if ($violations.Count -gt 0) {
  $report = "BALROG VIOLATION REPORT [$timestamp]`nMode: $Mode`nViolations: $($violations.Count)`n"
  foreach ($v in $violations) {
    $report += "`n[FAIL] $v"
  }

  # Write to log
  $logDir = "$ROOT\data\logs\balrog"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $report | Out-File "$logDir\balrog_$(Get-Date -Format 'yyyyMMdd_HHmmss').log" -Encoding UTF8

  # Telegram notifications temporarily disabled until Balrog has its own bot token.
  # powershell -File "$ROOT\scripts\claude-tasks\notify-asz.ps1" -Message $report

  Write-Output $report
  exit 1
} else {
  Write-Output "[$timestamp] Balrog $Mode check: ALL CLEAR"
  exit 0
}
