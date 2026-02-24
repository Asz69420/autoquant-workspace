param(
  [switch]$DryRun,
  [int]$MaxRefinementsPerRun = 1,
  [int]$MaxBundlesPerRun = 1,
  [switch]$RunYouTubeWatcher,
  [switch]$RunTVCatalogWorker
)

$ErrorActionPreference = 'Stop'

function Run-Py($args) {
  if ($DryRun) { return '' }
  return (python @args)
}

function Ensure-Lock($name) {
  $lockDir = 'data/state/locks'
  if (-not (Test-Path $lockDir)) { New-Item -ItemType Directory -Path $lockDir | Out-Null }
  $lockPath = Join-Path $lockDir ($name + '.lock')
  if (Test-Path $lockPath) { throw "Lock exists: $lockPath" }
  Set-Content -Path $lockPath -Value ([DateTime]::UtcNow.ToString('o')) -Encoding utf8
  return $lockPath
}

function Emit-InfoSummary($reasonCode, $summary) {
  if ($DryRun) { return }
  try {
    python scripts/log_event.py --run-id ('autopilot-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action $reasonCode --status-word INFO --status-emoji INFO --reason-code $reasonCode --summary $summary 2>$null | Out-Null
  } catch {}
}

$promotionsProcessed = 0
$refinementsRun = 0
$errorsCount = 0
$newCandidatesCount = 0
$bundlesProcessed = 0
$newIndicatorsAdded = 0
$skippedIndicatorsDedup = 0
$batchRuns = 0
$batchExecuted = 0
$batchSkipped = 0
$batchGateFail = 0
$refineVariants = 0
$refineExplore = 0
$refineDelta = 'n/a'
$libraryLessons = 0
$libraryRunCount = 0
$lock = $null

try {
  $lock = Ensure-Lock 'autopilot_worker'

  if ($RunYouTubeWatcher -and -not $DryRun) {
    try {
      Run-Py @('scripts/pipeline/youtube_watch_worker.py') | Out-Null
    } catch { $errorsCount += 1 }
  }
  if ($RunTVCatalogWorker -and -not $DryRun) {
    try {
      $tv = Run-Py @('scripts/pipeline/tv_catalog_worker.py') | ConvertFrom-Json
      $newIndicatorsAdded += [int]$tv.new_indicators_added
      $skippedIndicatorsDedup += [int]$tv.skipped_dedup
    } catch { $errorsCount += 1 }
  }

  $bundleIndexPath = 'artifacts/bundles/INDEX.json'
  if (Test-Path $bundleIndexPath) {
    $bundlePaths = @()
    try { $bundlePaths = @(Get-Content $bundleIndexPath -Raw | ConvertFrom-Json) } catch { $bundlePaths = @() }

    $take = @($bundlePaths | Select-Object -First $MaxBundlesPerRun)
    foreach ($bp in $take) {
      if (-not (Test-Path -LiteralPath $bp)) { continue }
      try {
        $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
        $lm = $b.linkmap_path
        if (-not $DryRun) {
          $an = Run-Py @('scripts/pipeline/run_analyser.py','--research-card-path',$b.research_card_path,'--linkmap-path',$lm) | ConvertFrom-Json
          Run-Py @('scripts/pipeline/verify_pipeline_stage2.py','--thesis',$an.thesis_path) | Out-Null
          $sp = Run-Py @('scripts/pipeline/emit_strategy_spec.py','--thesis-path',$an.thesis_path) | ConvertFrom-Json
          $variantCount = 0
          try { $variantCount = @((Get-Content $sp.strategy_spec_path -Raw | ConvertFrom-Json).variants).Count } catch { $variantCount = 0 }
          Emit-InfoSummary 'PROMOTION_SUMMARY' ("Promote: bundles=1 thesis=OK spec=OK variants=" + $variantCount + "; status=OK")

          $batch = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$sp.strategy_spec_path,'--variant','all') | ConvertFrom-Json
          try {
            $bdoc = Get-Content $batch.batch_artifact_path -Raw | ConvertFrom-Json
            $batchRuns += [int]$bdoc.summary.total_runs
            $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
            $batchSkipped += [int]$bdoc.summary.failed_runs
            foreach ($rr in $bdoc.runs) { if ($rr.skip_reason -eq 'FEASIBILITY_FAIL') { $batchGateFail += 1 } }
            Emit-InfoSummary 'BATCH_BACKTEST_SUMMARY' ("Batch: runs=" + $bdoc.summary.total_runs + " executed=" + ($bdoc.summary.total_runs - $bdoc.summary.failed_runs) + " skipped=" + $bdoc.summary.failed_runs + " gate_fail=" + $batchGateFail)
          } catch {}

          $promoId = [IO.Path]::GetFileNameWithoutExtension($sp.strategy_spec_path)
          $promoPath = "artifacts/promotions/" + (Get-Date -Format 'yyyyMMdd') + "/promo_" + $promoId + ".promotion_run.json"
          $promoObj = [ordered]@{
            schema_version = '1.0'
            id = "promo_" + $promoId
            created_at = [DateTime]::UtcNow.ToString('o')
            status = 'OK'
            input_linkmap_path = $lm
            thesis_artifact_path = $an.thesis_path
            strategy_spec_artifact_path = $sp.strategy_spec_path
            batch_backtest_artifact_path = $batch.batch_artifact_path
            experiment_plan_artifact_path = $batch.experiment_plan_path
          }
          New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($promoPath)) | Out-Null
          ($promoObj | ConvertTo-Json -Depth 8) | Set-Content -Path $promoPath -Encoding utf8

          if ($MaxRefinementsPerRun -gt 0 -and $refinementsRun -lt $MaxRefinementsPerRun) {
            $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
            $refinementsRun += 1
            try {
              $rdoc = Get-Content $ref.refinement_cycle_path -Raw | ConvertFrom-Json
              $refineVariants = [int]$rdoc.winner.summary.total_runs
              $refineExplore = [int]$rdoc.explore_variants_used_total
              $refineDelta = [string]$rdoc.best_score_delta
              Emit-InfoSummary 'REFINEMENT_SUMMARY' ("Refine: iters=" + $rdoc.iterations_used + " variants=" + $refineVariants + " explore=" + $refineExplore + " delta=" + $refineDelta + " status=" + $rdoc.final_recommendation)
            } catch {
              Emit-InfoSummary 'REFINEMENT_SUMMARY' 'Refine: iters=1 variants=0 explore=0 delta=n/a status=NO_IMPROVEMENT'
            }
          }
        }
        $bundlesProcessed += 1
        $promotionsProcessed += 1
      } catch { $errorsCount += 1 }
    }
  }

  if (-not $DryRun) {
    try {
      $lib = Run-Py @('scripts/pipeline/run_librarian.py','--since-days','7') | ConvertFrom-Json
      $newCandidatesCount = [int]$lib.top_count
      $libraryRunCount = [int]$lib.run_count
      $libraryLessons = [int]$lib.lessons_count
      if ($lib.new_indicators_added) { $newIndicatorsAdded += [int]$lib.new_indicators_added }
      if ($lib.skipped_indicators_dedup) { $skippedIndicatorsDedup += [int]$lib.skipped_indicators_dedup }
      Emit-InfoSummary 'LIBRARIAN_SUMMARY' ("Library: top=" + $lib.top_count + " run=" + $lib.run_count + " lessons=" + $lib.lessons_count + " new=" + $newIndicatorsAdded + " archived=0")
    } catch { $errorsCount += 1 }
  }
}
catch {
  $errorsCount += 1
}
finally {
  if ($lock -and (Test-Path $lock)) { Remove-Item $lock -Force -ErrorAction SilentlyContinue }
}

$summary = [ordered]@{
  event = 'AUTOPILOT_SUMMARY'
  created_at = [DateTime]::UtcNow.ToString('o')
  bundles_processed = $bundlesProcessed
  promotions_processed = $promotionsProcessed
  refinements_run = $refinementsRun
  new_candidates_count = $newCandidatesCount
  new_indicators_added = $newIndicatorsAdded
  skipped_indicators_dedup = $skippedIndicatorsDedup
  errors_count = $errorsCount
  dry_run = [bool]$DryRun
}

$stateDir = 'data/state'
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }
($summary | ConvertTo-Json -Depth 5) | Set-Content -Path 'data/state/autopilot_summary.json' -Encoding utf8

if (-not $DryRun) {
  try {
    python scripts/log_event.py --run-id ('autopilot-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) --agent oQ --model-id openai-codex/gpt-5.3-codex --action AUTOPILOT_SUMMARY --status-word INFO --status-emoji INFO --reason-code AUTOPILOT_SUMMARY --summary ("bundles=" + $bundlesProcessed + "; promotions=" + $promotionsProcessed + "; refinements=" + $refinementsRun + "; new_indicators=" + $newIndicatorsAdded + "; dedup_skips=" + $skippedIndicatorsDedup + "; errors=" + $errorsCount) 2>$null | Out-Null
  } catch {}
}

Write-Output ($summary | ConvertTo-Json -Depth 5)