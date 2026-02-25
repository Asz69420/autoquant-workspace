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
$tooLargeSkippedCount = 0
$refineVariants = 0
$refineExplore = 0
$refineDelta = 'n/a'
$libraryLessons = 0
$libraryRunCount = 0
$candidatesIngested = 0
$candidatesReachingRefinement = 0
$candidatesPassingGate = 0
$activeLibrarySize = 0
$insightNew = 0
$insightProcessed = 0
$insightFailed = 0
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
      if ($tv.too_large_skipped_count) { $tooLargeSkippedCount = [int]$tv.too_large_skipped_count }
      $gStatus = if ($grabberFailed -gt 0 -and $grabberFetched -eq 0) { 'FAIL' } elseif ($grabberFailed -gt 0 -or $grabberFetched -eq 0 -or $tooLargeSkippedCount -gt 0) { 'WARN' } else { 'OK' }
      Emit-Summary 'GRABBER_SUMMARY' ("Grabber: fetched=" + $grabberFetched + " dedup=" + $grabberDedup + " failed=" + $grabberFailed + " too_large_skipped_count=" + $tooLargeSkippedCount) $gStatus 'Grabber'
      $grabberEmitted = $true
    } catch {
      $errorsCount += 1
      Emit-Summary 'GRABBER_SUMMARY' 'Grabber: fetched=0 dedup=0 failed=0 too_large_skipped_count=0 (skipped: no indicator hints)' 'OK' 'Grabber'
      $grabberEmitted = $true
    }
  }

  if (-not $grabberEmitted -and -not $DryRun) {
    Emit-Summary 'GRABBER_SUMMARY' 'Grabber: fetched=0 dedup=0 failed=0 too_large_skipped_count=0 (skipped: no indicator hints)' 'OK' 'Grabber'
    $grabberEmitted = $true
  }

  if (-not $DryRun) {
    try {
      $insight = python scripts/pipeline/process_insight_cycle.py --max-refinements $MaxRefinementsPerRun --max-insights 1 | ConvertFrom-Json
      $insightNew = [int]$insight.new_processed
      $insightProcessed = [int]$insight.revisited
      $insightFailed = [int]$insight.failed
      if ($insightFailed -gt 0) { $errorsCount += $insightFailed }
      Emit-Summary 'INSIGHT_SUMMARY' ("Insight: new_processed=" + $insightNew + " revisited=" + $insightProcessed + " failed=" + $insightFailed) 'INFO' 'oQ'
    } catch {
      $insightFailed += 1
      $errorsCount += 1
      Emit-Summary 'INSIGHT_SUMMARY' ("Insight: new_processed=" + $insightNew + " revisited=" + $insightProcessed + " failed=" + $insightFailed) 'WARN' 'oQ'
    }
  }

  $bundleIndexPath = 'artifacts/bundles/INDEX.json'
  if (Test-Path $bundleIndexPath) {
    $bundlePaths = @()
    try { $bundlePaths = @(Get-Content $bundleIndexPath -Raw | ConvertFrom-Json) } catch { $bundlePaths = @() }

    $bundleSlotsUsed = 0
    foreach ($bp in $bundlePaths) {
      if ($bundleSlotsUsed -ge $MaxBundlesPerRun) { break }
      if (-not (Test-Path -LiteralPath $bp)) { continue }
      try {
        $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
        if ($b.status -eq 'BLOCKED' -and $b.reason_code -eq 'COMPONENT_TOO_LARGE') { continue }
        $lm = $b.linkmap_path

        $componentType = 'INDICATOR'
        $componentTooLarge = $false
        $componentReason = ''
        try {
          $indPaths = @()
          if ($b.indicator_record_paths) { $indPaths = @($b.indicator_record_paths) }
          if ($indPaths.Count -eq 0 -and $lm -and (Test-Path $lm)) {
            $lmObj = Get-Content $lm -Raw | ConvertFrom-Json
            if ($lmObj.indicator_record_paths) { $indPaths = @($lmObj.indicator_record_paths) }
          }
          if ($indPaths.Count -gt 0 -and (Test-Path $indPaths[0])) {
            $irObj = Get-Content $indPaths[0] -Raw | ConvertFrom-Json
            if ($irObj.component_type) { $componentType = [string]$irObj.component_type }
            if ($null -ne $irObj.pine_too_large) { $componentTooLarge = [bool]$irObj.pine_too_large }
          }
        } catch {}

        if (-not $DryRun) {
          if ($componentTooLarge) {
            $tooLargeSkippedCount += 1
            try {
              $b.status = 'BLOCKED'
              $b.reason_code = 'COMPONENT_TOO_LARGE'
              ($b | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $bp -Encoding utf8
            } catch {}
            Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=SKIPPED spec=BLOCKED variants=0 status=BLOCKED reason=COMPONENT_TOO_LARGE summary=Component too large; skipped' 'WARN' 'Promotion'
            $promotionEmitted = $true
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: COMPONENT_TOO_LARGE)' 'WARN' 'Backtester'
            $batchEmitted = $true
            Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED (COMPONENT_TOO_LARGE)' 'WARN' 'Refinement'
            $refineEmitted = $true
            $bundlesProcessed += 1
            $bundleSlotsUsed += 1
            continue
          }

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
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'OK' 'Backtester'
            $batchEmitted = $true
          } else {
            try {
              $batch = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$sp.strategy_spec_path,'--variant','all') | ConvertFrom-Json
              $bdoc = Get-Content $batch.batch_artifact_path -Raw | ConvertFrom-Json
              $batchRuns += [int]$bdoc.summary.total_runs
              $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
              $batchSkipped += [int]$bdoc.summary.failed_runs
              foreach ($rr in $bdoc.runs) {
                if ($rr.skip_reason -eq 'FEASIBILITY_FAIL') { $batchGateFail += 1 }
                if ($rr.gate_pass -eq $true) { $candidatesPassingGate += 1 }
              }
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
            Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'OK' 'Refinement'
            $refineEmitted = $true
          } elseif ($MaxRefinementsPerRun -gt 0 -and $refinementsRun -lt $MaxRefinementsPerRun) {
            $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
            $refinementsRun += 1
            $candidatesReachingRefinement += 1
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
        $bundleSlotsUsed += 1
      } catch { $errorsCount += 1 }
    }
  }

  if (-not $batchEmitted -and -not $DryRun) {
    Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'OK' 'Backtester'
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
        $activeLibrarySize = ([int]$topCountActual + [int]$runCountActual + [int]$lessCountActual)
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
      Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=0 thesis=SKIPPED spec=SKIPPED variants=0 status=SKIPPED' 'OK' 'Promotion'
      $promotionEmitted = $true
    }
    if (-not $batchEmitted) {
      Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 gate_fail=0 (skipped: no variants)' 'OK' 'Backtester'
      $batchEmitted = $true
    }
    if (-not $refineEmitted) {
      Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'OK' 'Refinement'
      $refineEmitted = $true
    }
    if (-not $libraryEmitted) {
      Emit-Summary 'LIBRARIAN_SUMMARY' 'Library: (skipped: not run)' 'OK' 'Librarian'
      $libraryEmitted = $true
    }
  }
  if ($lock -and (Test-Path $lock)) { Remove-Item $lock -Force -ErrorAction SilentlyContinue }
}

$candidatesIngested = $bundlesProcessed

$summary = [ordered]@{
  event = 'AUTOPILOT_SUMMARY'
  created_at = [DateTime]::UtcNow.ToString('o')
  bundles_processed = $bundlesProcessed
  promotions_processed = $promotionsProcessed
  refinements_run = $refinementsRun
  new_candidates_count = $newCandidatesCount
  candidates_ingested = $candidatesIngested
  candidates_reaching_refinement = $candidatesReachingRefinement
  candidates_passing_gate = $candidatesPassingGate
  active_library_size = $activeLibrarySize
  new_indicators_added = $newIndicatorsAdded
  skipped_indicators_dedup = $skippedIndicatorsDedup
  errors_count = $errorsCount
  dry_run = [bool]$DryRun
  insight_new = $insightNew
  insight_processed = $insightProcessed
  insight_failed = $insightFailed
}

$stateDir = 'data/state'
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }

$countersPath = Join-Path $stateDir 'autopilot_counters.json'
$counters = [ordered]@{ starvation_cycles = 0; drought_cycles = 0; updated_at = [DateTime]::UtcNow.ToString('o') }
if (Test-Path $countersPath) {
  try {
    $prev = Get-Content $countersPath -Raw | ConvertFrom-Json
    if ($null -ne $prev.starvation_cycles) { $counters.starvation_cycles = [int]$prev.starvation_cycles }
    if ($null -ne $prev.drought_cycles) { $counters.drought_cycles = [int]$prev.drought_cycles }
  } catch {}
}

if ([int]$candidatesReachingRefinement -eq 0) { $counters.starvation_cycles = [int]$counters.starvation_cycles + 1 } else { $counters.starvation_cycles = 0 }
if ([int]$candidatesPassingGate -eq 0) { $counters.drought_cycles = [int]$counters.drought_cycles + 1 } else { $counters.drought_cycles = 0 }
$counters.updated_at = [DateTime]::UtcNow.ToString('o')
($counters | ConvertTo-Json -Depth 5) | Set-Content -Path $countersPath -Encoding utf8

$summary.starvation_cycles = [int]$counters.starvation_cycles
$summary.drought_cycles = [int]$counters.drought_cycles

($summary | ConvertTo-Json -Depth 5) | Set-Content -Path 'data/state/autopilot_summary.json' -Encoding utf8

if (-not $DryRun) {
  if ([int]$counters.starvation_cycles -ge 12) {
    Emit-Summary 'AUTOPILOT_STARVATION_WARN' ("Autopilot starvation: starvation_cycles=" + $counters.starvation_cycles + " candidates_reaching_refinement=" + $candidatesReachingRefinement) 'WARN' 'oQ'
  }
  if ([int]$counters.drought_cycles -ge 30) {
    Emit-Summary 'AUTOPILOT_DROUGHT_WARN' ("Autopilot drought: drought_cycles=" + $counters.drought_cycles + " candidates_passing_gate=" + $candidatesPassingGate) 'WARN' 'oQ'
  }

  $aStatus = if ($errorsCount -gt 0) { 'FAIL' } else { 'OK' }
  Emit-Summary 'AUTOPILOT_SUMMARY' ("Autopilot: ingested=" + $candidatesIngested + " reached_refinement=" + $candidatesReachingRefinement + " passing_gate=" + $candidatesPassingGate + " active_library_size=" + $activeLibrarySize + " bundles=" + $bundlesProcessed + " promotions=" + $promotionsProcessed + " refinements=" + $refinementsRun + " errors=" + $errorsCount) $aStatus 'oQ'
}

Write-Output ($summary | ConvertTo-Json -Depth 5)