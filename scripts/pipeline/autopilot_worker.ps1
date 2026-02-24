param(
  [switch]$DryRun,
  [int]$MaxRefinementsPerRun = 1
)

$ErrorActionPreference = 'Stop'

function Run-Py($args) {
  if ($DryRun) { return '' }
  return (python @args)
}

$promotionsProcessed = 0
$refinementsRun = 0
$errorsCount = 0
$newCandidatesCount = 0

try {
  $linkmaps = Get-ChildItem artifacts/links -Recurse -Filter *.linkmap.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
  if ($linkmaps.Count -gt 0) {
    # bounded: newest only
    $lm = $linkmaps[0].FullName
    if (-not $DryRun) {
      $o = Run-Py @('scripts/pipeline/run_analyser.py','--research-card-path','artifacts/research/20260224/research-20260224-6a4dd103b40d.research_card.json','--linkmap-path',$lm)
      $th = ($o | ConvertFrom-Json).thesis_path
      Run-Py @('scripts/pipeline/verify_pipeline_stage2.py','--thesis',$th) | Out-Null
      $s = Run-Py @('scripts/pipeline/emit_strategy_spec.py','--thesis-path',$th)
      $sp = ($s | ConvertFrom-Json).strategy_spec_path
      Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$sp,'--variant','all') | Out-Null
    }
    $promotionsProcessed = 1
  }
} catch {
  $errorsCount += 1
}

try {
  if ($MaxRefinementsPerRun -gt 0) {
    $promos = Get-ChildItem artifacts/promotions -Recurse -Filter *.promotion_run.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($promos.Count -gt 0 -and -not $DryRun) {
      Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promos[0].FullName) | Out-Null
      $refinementsRun = 1
    }
  }
} catch {
  $errorsCount += 1
}

try {
  if (-not $DryRun) {
    $lib = Run-Py @('scripts/pipeline/run_librarian.py','--since-days','7')
    $newCandidatesCount = [int](($lib | ConvertFrom-Json).top_count)
  }
} catch {
  $errorsCount += 1
}

$summary = [ordered]@{
  event = 'AUTOPILOT_SUMMARY'
  created_at = [DateTime]::UtcNow.ToString('o')
  promotions_processed = $promotionsProcessed
  refinements_run = $refinementsRun
  new_candidates_count = $newCandidatesCount
  errors_count = $errorsCount
  dry_run = [bool]$DryRun
}

$stateDir = 'data/state'
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }
($summary | ConvertTo-Json -Depth 4) | Set-Content -Path 'data/state/autopilot_summary.json' -Encoding utf8

if (-not $DryRun) {
  try {
    python scripts/log_event.py --run-id ('autopilot-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action AUTOPILOT_SUMMARY --status-word INFO --status-emoji INFO --summary ("promotions=" + $promotionsProcessed + "; refinements=" + $refinementsRun + "; new_candidates=" + $newCandidatesCount + "; errors=" + $errorsCount) 2>$null | Out-Null
  } catch {}
}

Write-Output ($summary | ConvertTo-Json -Depth 4)
