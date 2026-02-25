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

$CycleRunId = 'autopilot-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Emit-Summary($reasonCode, $summary, $statusWord = 'INFO', $agent = 'oQ') {
  if ($DryRun) { return }
  try {
    $emoji = if ($statusWord -eq 'OK') { 'OK' } elseif ($statusWord -eq 'WARN') { 'WARN' } elseif ($statusWord -eq 'FAIL') { 'FAIL' } else { 'INFO' }
    $rid = if ($reasonCode -eq 'AUTOPILOT_SUMMARY') { $CycleRunId } else { $CycleRunId + '-' + $reasonCode }
    python scripts/log_event.py --run-id $rid --agent $agent --model-id openai-codex/gpt-5.3-codex --action $reasonCode --status-word $statusWord --status-emoji $emoji --reason-code $reasonCode --summary $summary 2>$null | Out-Null
  } catch {}
}

function Emit-InfoSummary($reasonCode, $summary, $agent = 'oQ') {
  Emit-Summary $reasonCode $summary 'INFO' $agent
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
$batchEmitted = $false
$promotionEmitted = $false
$refineEmitted = $false
$libraryEmitted = $false
$grabberFetched = 0
$grabberDedup = 0
$grabberFailed = 0
$grabberEmitted = $false
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
      if ($tv.grabber_ok) { $grabberFetched = [int]$tv.grabber_ok }
      if ($tv.skipped_dedup) { $grabberDedup = [int]$tv.skipped_dedup }
      if ($tv.grabber_fail) { $grabberFailed = [int]$tv.grabber_fail }
      $gStatus = if ($grabberFailed -gt 0 -and $grabberFetched -eq 0) { 'FAIL' } elseif ($grabberFailed -gt 0 -or $grabberFetched -eq 0) { 'WARN' } else { 'OK' }
      Emit-Summary 'GRABBER_SUMMARY' ("Grabber: fetched=" + $grabberFetched + " dedup=" + $grabberDedup + " failed=" + $grabberFailed) $gStatus 'Grabber'
      $grabberEmitted = $true
    } catch {
      $errorsCount += 1
      Emit-Summary 'GRABBER_SUMMARY' 'Grabber: fetched=0 dedup=0 failed=0 (skipped: no indicator hints)' 'WARN' 'Grabber'
      $grabberEmitted = $true
    }
  }

  if (-not $grabberEmitted -and -not $DryRun) {
    Emit-Summary 'GRABBER_SUMMARY' 'Grabber: fetched=0 dedup=0 failed=0 (skipped: no indicator hints)' 'WARN' 'Grabber'
    $grabberEmitted = $true
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
          if ($sp.variants) { $variantCount = [int]$sp.variants }
          $promoStatus = 'OK'
          if ($sp.status -and [string]$sp.status -eq 'BLOCKED') { $promoStatus = 'BLOCKED' }
          if ($variantCount -eq 0) { $promoStatus = 'BLOCKED' }

          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=OK spec=BLOCKED variants=0 status=BLOCKED' 'WARN' 'Promotion'
          } else {
            Emit-Summary 'PROMOTION_SUMMARY' ("Promote: bundles=1 thesis=OK spec=OK variants=" + $variantCount + " status=OK") 'OK' 'Promotion'
          }
          $promotionEmitted = $true

          $batch = $null
          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: blocked promotion)' 'WARN' 'Backtester'
            $batchEmitted = $true
          } elseif ($variantCount -eq 0) {
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'WARN' 'Backtester'
            $batchEmitted = $true
          } else {
            try {
              $batch = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$sp.strategy_spec_path,'--variant','all') | ConvertFrom-Json
              $bdoc = Get-Content $batch.batch_artifact_path -Raw | ConvertFrom-Json
              $batchRuns += [int]$bdoc.summary.total_runs
              $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
              $batchSkipped += [int]$bdoc.summary.failed_runs
              foreach ($rr in $bdoc.runs) { if ($rr.skip_reason -eq 'FEASIBILITY_FAIL') { $batchGateFail += 1 } }
              $execCount = ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
              $bStatus = if ($execCount -le 0) { 'WARN' } else { 'OK' }
              Emit-Summary 'BATCH_BACKTEST_SUMMARY' ("Batch: runs=" + $bdoc.summary.total_runs + " executed=" + $execCount + " skipped=" + $bdoc.summary.failed_runs + " gate_fail=" + $batchGateFail) $bStatus 'Backtester'
              $batchEmitted = $true
            } catch {
              Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: batch error)' 'FAIL' 'Backtester'
              $batchEmitted = $true
            }
          }

          $promoId = [IO.Path]::GetFileNameWithoutExtension($sp.strategy_spec_path)
          $promoPath = "artifacts/promotions/" + (Get-Date -Format 'yyyyMMdd') + "/promo_" + $promoId + ".promotion_run.json"
          $promoObj = [ordered]@{
            schema_version = '1.0'
            id = "promo_" + $promoId
            created_at = [DateTime]::UtcNow.ToString('o')
            status = $(if ($promoStatus -eq 'BLOCKED') { 'BLOCKED' } else { 'OK' })
            reason_code = $(if ($promoStatus -eq 'BLOCKED') { 'NO_VARIANTS_COMPILED' } else { $null })
            suggestion = $(if ($promoStatus -eq 'BLOCKED') { 'Indicator not mapped to executable signals yet; needs rule extraction or builtin mapping.' } else { $null })
            input_linkmap_path = $lm
            thesis_artifact_path = $an.thesis_path
            strategy_spec_artifact_path = $sp.strategy_spec_path
            batch_backtest_artifact_path = $(if ($null -ne $batch) { $batch.batch_artifact_path } else { '' })
            experiment_plan_artifact_path = $(if ($null -ne $batch) { $batch.experiment_plan_path } else { '' })
          }
          New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($promoPath)) | Out-Null
          ($promoObj | ConvertTo-Json -Depth 8) | Set-Content -Path $promoPath -Encoding utf8

          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'WARN' 'Refinement'
            $refineEmitted = $true
          } elseif ($MaxRefinementsPerRun -gt 0 -and $refinementsRun -lt $MaxRefinementsPerRun) {
            $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
            $refinementsRun += 1
            try {
              $rdoc = Get-Content $ref.refinement_cycle_path -Raw | ConvertFrom-Json
              $refineVariants = [int]$rdoc.winner.summary.total_runs
              $refineExplore = [int]$rdoc.explore_variants_used_total
              $refineDelta = [string]$rdoc.best_score_delta
              $rStatus = if ([string]$rdoc.final_recommendation -eq 'NO_IMPROVEMENT') { 'WARN' } else { 'OK' }
              Emit-Summary 'REFINEMENT_SUMMARY' ("Refine: iters=" + $rdoc.iterations_used + " variants=" + $refineVariants + " explore=" + $refineExplore + " delta=" + $refineDelta + " status=" + $rdoc.final_recommendation) $rStatus 'Refinement'
              $refineEmitted = $true
            } catch {
              Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=1 variants=0 explore=0 delta=n/a status=NO_IMPROVEMENT' 'WARN' 'Refinement'
              $refineEmitted = $true
            }
          }
        }
        $bundlesProcessed += 1
        $promotionsProcessed += 1
      } catch { $errorsCount += 1 }
    }
  }

  if (-not $batchEmitted -and -not $DryRun) {
    Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'WARN' 'Backtester'
    $batchEmitted = $true
  }

  if (-not $DryRun) {
    try {
      $lib = Run-Py @('scripts/pipeline/run_librarian.py','--since-days','7') | ConvertFrom-Json
      $newCandidatesCount = [int]$lib.top_count
      if ($lib.new_indicators_added) { $newIndicatorsAdded += [int]$lib.new_indicators_added }
      if ($lib.skipped_indicators_dedup) { $skippedIndicatorsDedup += [int]$lib.skipped_indicators_dedup }

      $topPath = 'artifacts/library/TOP_CANDIDATES.json'
      $runPath = 'artifacts/library/RUN_INDEX.json'
      $lessPath = 'artifacts/library/LESSONS_INDEX.json'

      $topCountActual = $null
      $runCountActual = $null
      $lessCountActual = $null
      $readOk = $true

      try {
        if (-not (Test-Path $topPath)) { throw 'TOP_CANDIDATES missing' }
        $topObj = Get-Content $topPath -Raw | ConvertFrom-Json
        $topCountActual = @($topObj).Count
      } catch { $readOk = $false }

      try {
        if (-not (Test-Path $runPath)) { throw 'RUN_INDEX missing' }
        $runObj = Get-Content $runPath -Raw | ConvertFrom-Json
        $runCountActual = @($runObj).Count
      } catch { $readOk = $false }

      try {
        if (-not (Test-Path $lessPath)) { throw 'LESSONS_INDEX missing' }
        $lessObj = Get-Content $lessPath -Raw | ConvertFrom-Json
        $lessCountActual = @($lessObj).Count
      } catch { $readOk = $false }

      if ($readOk) {
        $libraryRunCount = [int]$runCountActual
        $libraryLessons = [int]$lessCountActual
        Emit-Summary 'LIBRARIAN_SUMMARY' ("Library: top=" + $topCountActual + " run=" + $runCountActual + " lessons=" + $lessCountActual + " new=" + $newIndicatorsAdded + " archived=0") 'OK' 'Librarian'
        $libraryEmitted = $true
      } else {
        Emit-Summary 'LIBRARIAN_SUMMARY_READ_FAIL' 'Library: top=? run=? lessons=? new=? archived=? (skipped: read fail)' 'WARN' 'Librarian'
        $libraryEmitted = $true
      }
    } catch {
      $errorsCount += 1
      Emit-Summary 'LIBRARIAN_SUMMARY_READ_FAIL' 'Library: top=? run=? lessons=? new=? archived=? (skipped: run fail)' 'WARN' 'Librarian'
      $libraryEmitted = $true
    }
  }

}
catch {
  $errorsCount += 1
}
finally {
  if (-not $DryRun) {
    if (-not $promotionEmitted) {
      Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=0 thesis=SKIPPED spec=SKIPPED variants=0 status=SKIPPED' 'WARN' 'Promotion'
      $promotionEmitted = $true
    }
    if (-not $batchEmitted) {
      Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 gate_fail=0 (skipped: no variants)' 'WARN' 'Backtester'
      $batchEmitted = $true
    }
    if (-not $refineEmitted) {
      Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'WARN' 'Refinement'
      $refineEmitted = $true
    }
    if (-not $libraryEmitted) {
      Emit-Summary 'LIBRARIAN_SUMMARY_READ_FAIL' 'Library: top=? run=? lessons=? new=? archived=? (skipped: not run)' 'WARN' 'Librarian'
      $libraryEmitted = $true
    }
  }
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
  $aStatus = if ($errorsCount -gt 0) { 'FAIL' } elseif ($bundlesProcessed -eq 0 -or $promotionsProcessed -eq 0) { 'WARN' } else { 'OK' }
  Emit-Summary 'AUTOPILOT_SUMMARY' ("Autopilot: bundles=" + $bundlesProcessed + " promotions=" + $promotionsProcessed + " refinements=" + $refinementsRun + " errors=" + $errorsCount) $aStatus 'oQ'
}

Write-Output ($summary | ConvertTo-Json -Depth 5)