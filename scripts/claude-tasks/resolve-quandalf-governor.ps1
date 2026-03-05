param(
  [Parameter(Mandatory = $true)]
  [string]$Mode,
  [Parameter(Mandatory = $true)]
  [string]$Root
)

$cfgPath = Join-Path $Root 'config\quandalf_governor.json'
if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing governor config: $cfgPath"
}

$cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
$defaultTier = [string]$cfg.default_tier
if ([string]::IsNullOrWhiteSpace($defaultTier)) { $defaultTier = 'standard' }
$tier = [string]$cfg.mode_defaults.$Mode
if ([string]::IsNullOrWhiteSpace($tier)) { $tier = $defaultTier }

$ordersPath = Join-Path $Root 'docs\shared\QUANDALF_ORDERS.md'
$hasPendingOrder = $false
if (Test-Path -LiteralPath $ordersPath) {
  try {
    $txt = Get-Content -LiteralPath $ordersPath -Raw -Encoding UTF8
    if ($txt -match '(?i)\*\*Status:\*\*\s*(PENDING|NEW)') { $hasPendingOrder = $true }
  } catch {}
}

if (($cfg.escalation.pending_order_to_deep -eq $true) -and $hasPendingOrder -and @('strategy_generator','strategy_researcher') -contains $Mode) {
  $tier = 'deep'
}

if ($cfg.escalation.rate_limit_downgrade_to_lite -eq $true) {
  $logsDir = Join-Path $Root 'data\logs\claude-tasks'
  if (Test-Path -LiteralPath $logsDir) {
    $latest = Get-ChildItem -LiteralPath $logsDir -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match "^$([regex]::Escape(($Mode -replace 'strategy_','' -replace '_synthesizer','' -replace 'backtest_','bt_')))_" } |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
      try {
        $t = Get-Content -LiteralPath $latest.FullName -Raw -Encoding UTF8
        if ($t -match '(?i)hit your limit|rate\s*limit|too\s*many\s*requests|\b429\b') {
          $tier = 'lite'
        }
      } catch {}
    }
  }
}

$limits = $cfg.tiers.$tier
if ($null -eq $limits) { $limits = $cfg.tiers.standard; $tier = 'standard' }

[PSCustomObject]@{
  tier = $tier
  max_outcome_notes = [int]$limits.max_outcome_notes
  max_backtest_hours = [int]$limits.max_backtest_hours
  max_backtest_results = [int]$limits.max_backtest_results
  max_research_cards = [int]$limits.max_research_cards
  max_claude_specs = [int]$limits.max_claude_specs
  max_library_rows = [int]$limits.max_library_rows
  pending_order = [bool]$hasPendingOrder
}
