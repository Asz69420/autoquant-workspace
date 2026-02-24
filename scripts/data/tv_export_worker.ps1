param(
  [string]$Config = 'config/tv_export_targets.json',
  [string]$Target = 'eth_perp_15m',
  [string]$IncrementalCsv,
  [string]$DeepCsv
)

$ErrorActionPreference = 'Stop'
$pass = 0; $partial = 0; $fail = 0

if (-not [string]::IsNullOrWhiteSpace($IncrementalCsv)) {
  $inc = python scripts/data/export_tradingview_csv.py --config $Config --target $Target --mode incremental --source-csv $IncrementalCsv | ConvertFrom-Json
  if ($inc.status -eq 'PASS') { $pass++ } elseif ($inc.status -eq 'PARTIAL') { $partial++ } else { $fail++ }
}

if (-not [string]::IsNullOrWhiteSpace($DeepCsv)) {
  $deep = python scripts/data/export_tradingview_csv.py --config $Config --target $Target --mode deep --source-csv $DeepCsv --simulate-plateau | ConvertFrom-Json
  if ($deep.status -eq 'PASS') { $pass++ } elseif ($deep.status -eq 'PARTIAL') { $partial++ } else { $fail++ }
}

$status = if ($fail -gt 0) { 'FAIL' } elseif ($partial -gt 0) { 'PARTIAL' } else { 'PASS' }
python scripts/log_event.py --run-id ('tv-export-'+[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action tv_export_worker --status-word $status --status-emoji 'ℹ️' --reason-code TV_EXPORT_SUMMARY --summary ("exported="+$pass+" partial="+$partial+" failed="+$fail) | Out-Null

Write-Output ("TV_EXPORT_SUMMARY status="+$status+" exported="+$pass+" partial="+$partial+" failed="+$fail)
