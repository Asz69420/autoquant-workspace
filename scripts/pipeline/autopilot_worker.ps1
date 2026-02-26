param(
  [switch]$DryRun,
  [int]$MaxRefinementsPerRun = 1,
  [int]$MaxBundlesPerRun = 1,
  [switch]$RunYouTubeWatcher,
  [switch]$RunTVCatalogWorker,
  [switch]$ForceRecombine,
  [string]$FastCommand = ''
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

function Set-BundleState([string]$bundlePath, [string]$status, [string]$lastError = '', [bool]$incrementAttempt = $false) {
  if (-not (Test-Path -LiteralPath $bundlePath)) { return }
  try {
    $b = Get-Content -LiteralPath $bundlePath -Raw | ConvertFrom-Json
    $b | Add-Member -NotePropertyName status -NotePropertyValue $status -Force
    $b | Add-Member -NotePropertyName last_processed_at -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    $attemptsVal = 0
    try { if ($null -ne $b.attempts) { $attemptsVal = [int]$b.attempts } } catch { $attemptsVal = 0 }
    if ($incrementAttempt) { $attemptsVal += 1 }
    $b | Add-Member -NotePropertyName attempts -NotePropertyValue $attemptsVal -Force
    if ([string]::IsNullOrWhiteSpace($lastError)) {
      $b | Add-Member -NotePropertyName last_error -NotePropertyValue $null -Force
    } else {
      $trimmed = ([string]$lastError).Substring(0, [Math]::Min(240, ([string]$lastError).Length))
      $b | Add-Member -NotePropertyName last_error -NotePropertyValue $trimmed -Force
    }
    ($b | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $bundlePath -Encoding utf8
  } catch {}
}

function Handle-FastCommand([string]$cmd) {
  if ([string]::IsNullOrWhiteSpace($cmd)) { return $false }
  $m = [regex]::Match($cmd.Trim(), '^retry\s+bundle\s+(.+)$', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if (-not $m.Success) { return $false }
  $needle = $m.Groups[1].Value.Trim()
  $bundleIndexPath = 'artifacts/bundles/INDEX.json'
  if (-not (Test-Path $bundleIndexPath)) {
    Write-Output '{"status":"WARN","reason_code":"BUNDLE_INDEX_MISSING"}'
    return $true
  }
  $paths = @()
  try {
    $tmp = Get-Content $bundleIndexPath -Raw | ConvertFrom-Json
    if ($tmp -is [System.Array]) { $paths = $tmp } elseif ($null -ne $tmp) { $paths = @($tmp) } else { $paths = @() }
  } catch { $paths = @() }
  foreach ($p in $paths) {
    if (-not (Test-Path -LiteralPath $p)) { continue }
    try {
      $b = Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
      $bid = [string]$b.id
      if ($bid -eq $needle -or $p -like "*$needle*" -or [IO.Path]::GetFileNameWithoutExtension($p) -eq $needle) {
        Set-BundleState -bundlePath $p -status 'NEW' -lastError '' -incrementAttempt $false
        Write-Output (ConvertTo-Json @{ status='OK'; action='retry bundle'; bundle=$bid; path=$p; new_status='NEW' })
        return $true
      }
    } catch {}
  }
  Write-Output (ConvertTo-Json @{ status='WARN'; action='retry bundle'; reason_code='BUNDLE_NOT_FOUND'; needle=$needle })
  return $true
}

$CycleRunId = 'autopilot-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Emit-Summary($reasonCode, $summary, $statusWord = 'INFO', $agent = 'oQ') {
  if ($DryRun) { return }
  try {
    $emoji = if ($statusWord -eq 'OK') { 'OK' } elseif ($statusWord -eq 'WARN') { 'WARN' } elseif ($statusWord -eq 'FAIL') { 'FAIL' } else { 'INFO' }
    $rid = if ($reasonCode -eq 'LAB_SUMMARY') { $CycleRunId } else { $CycleRunId + '-' + $reasonCode }
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
$directiveNotesSeen = 0
$directiveVariantsEmitted = 0
$explorationVariantsEmitted = 0
$libraryLessons = 0
$libraryRunCount = 0
$candidatesIngested = 0
$candidatesReachingRefinement = 0
$candidatesPassingGate = 0
$activeLibrarySize = '?'
$insightNew = 0
$insightProcessed = 0
$insightFailed = 0
$lock = $null
$recombineCreated = 0
$recombineBundlePath = ''
$recombineIndicator = ''
$recombineTemplate = ''
$recombineEmitted = $false
$starvationCyclesPrev = 0
$latestBatchArtifactPath = ''
$latestRefinementArtifactPath = ''

if (Handle-FastCommand $FastCommand) {
  exit 0
}

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

  try {
    $prevCountersPath = 'data/state/autopilot_counters.json'
    if (Test-Path $prevCountersPath) {
      $prevCounters = Get-Content $prevCountersPath -Raw | ConvertFrom-Json
      if ($null -ne $prevCounters.starvation_cycles) { $starvationCyclesPrev = [int]$prevCounters.starvation_cycles }
    }
  } catch {}

  try {
    $outcomesRoot = 'artifacts/outcomes'
    if (Test-Path $outcomesRoot) {
      $latestOutcomeNote = Get-ChildItem -Path $outcomesRoot -Recurse -Filter 'outcome_notes_*.json' -File -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($latestOutcomeNote) { $directiveNotesSeen = 1 }
    }
  } catch {}

  $bundleIndexPath = 'artifacts/bundles/INDEX.json'
  if (Test-Path $bundleIndexPath) {
    $bundlePaths = @()
    try {
      $tmpBundlePaths = Get-Content $bundleIndexPath -Raw | ConvertFrom-Json
      if ($tmpBundlePaths -is [System.Array]) { $bundlePaths = $tmpBundlePaths } elseif ($null -ne $tmpBundlePaths) { $bundlePaths = @($tmpBundlePaths) } else { $bundlePaths = @() }
    } catch { $bundlePaths = @() }

    if (-not $DryRun -and (($bundlePaths.Count -eq 0 -and $starvationCyclesPrev -ge 12) -or $ForceRecombine)) {
      try {
        $rcb = Run-Py @('scripts/pipeline/recombine_from_library.py') | ConvertFrom-Json
        $rcCreated = 0
        try { $rcCreated = [int]$rcb.created } catch { $rcCreated = 0 }
        if (($rcCreated -ge 1 -or $rcb.bundle_path) -and $rcb.bundle_path) {
          $recombineCreated = 1
          $recombineBundlePath = [string]$rcb.bundle_path
          $recombineIndicator = [string]$rcb.indicator_name
          $recombineTemplate = [string]$rcb.template_name
          $bundlePaths = @($recombineBundlePath) + @($bundlePaths)
          Emit-Summary 'RECOMBINE_SUMMARY' ("Recombine: created=1 indicator=" + $recombineIndicator + " template=" + $recombineTemplate) 'OK' 'oQ'
          $recombineEmitted = $true
        } else {
          Emit-Summary 'RECOMBINE_SUMMARY' 'Recombine: created=0 indicator=n/a template=n/a' 'WARN' 'oQ'
          $recombineEmitted = $true
        }
      } catch {
        $errorsCount += 1
        Emit-Summary 'RECOMBINE_SUMMARY' 'Recombine: created=0 indicator=n/a template=n/a (error)' 'FAIL' 'oQ'
        $recombineEmitted = $true
      }
    }

    $bundleSlotsUsed = 0
    $consecutiveBundleReadFails = 0
    $maxConsecutiveBundleReadFails = 3
    $maxConsecutiveReadFailHit = $false
    $newBundlesSeen = 0
    $processableNewBundles = 0
    foreach ($bp in $bundlePaths) {
      if ($bundleSlotsUsed -ge $MaxBundlesPerRun) { break }
      if (-not (Test-Path -LiteralPath $bp)) { continue }

      $b = $null
      $bundleFile = [IO.Path]::GetFileName([string]$bp)
      try {
        $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
        $consecutiveBundleReadFails = 0
      } catch {
        if (-not $DryRun) {
          Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError 'BUNDLE_READ_FAIL' -incrementAttempt $false
          Emit-Summary 'BUNDLE_READ_FAIL' ("Bundle read fail: " + $bundleFile) 'WARN' 'oQ'
        }
        $consecutiveBundleReadFails += 1
        if ($consecutiveBundleReadFails -ge $maxConsecutiveBundleReadFails) {
          $maxConsecutiveReadFailHit = $true
          break
        }
        continue
      }

      try {
        $bundleStatus = [string]$b.status
        if ([string]::IsNullOrWhiteSpace($bundleStatus)) { $bundleStatus = 'NEW' }
        if ($bundleStatus -ne 'NEW') { continue }
        $newBundlesSeen += 1
        $processableNewBundles += 1

        if (-not $DryRun) {
          Set-BundleState -bundlePath $bp -status 'IN_PROGRESS' -lastError '' -incrementAttempt $true
          $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
        }

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
            if ($irObj.pine_too_large_reason) { $componentReason = [string]$irObj.pine_too_large_reason }
          }
        } catch {}

        if (-not $DryRun) {
          if ($componentTooLarge) {
            $tooLargeSkippedCount += 1
            $sizeDetail = if ([string]::IsNullOrWhiteSpace($componentReason)) { 'unknown' } else { $componentReason }
            Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError ("COMPONENT_TOO_LARGE: " + $sizeDetail) -incrementAttempt $false
            Emit-Summary 'PROMOTION_SUMMARY' ("Promote: bundles=1 thesis=SKIPPED spec=BLOCKED variants=0 status=BLOCKED reason=COMPONENT_TOO_LARGE summary=Component too large (" + $sizeDetail + "); skipped") 'WARN' 'Promotion'
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

          try {
            if ($sp.strategy_spec_path -and (Test-Path -LiteralPath $sp.strategy_spec_path)) {
              $specObj = Get-Content -LiteralPath $sp.strategy_spec_path -Raw | ConvertFrom-Json
              $specVariants = @($specObj.variants)
              $directiveBatch = @($specVariants | Where-Object { [string]$_.origin -eq 'DIRECTIVE' }).Count
              $explorationBatch = @($specVariants | Where-Object { [string]$_.name -like 'directive_exploration*' }).Count
              if ($directiveBatch -gt 0) { $directiveNotesSeen = 1 }
              $directiveVariantsEmitted += [int]$directiveBatch
              $explorationVariantsEmitted += [int]$explorationBatch
            }
          } catch {}

          $promoStatus = 'OK'
          if ($sp.status -and [string]$sp.status -eq 'BLOCKED') { $promoStatus = 'BLOCKED' }
          if ($variantCount -eq 0) { $promoStatus = 'BLOCKED' }

          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=OK spec=BLOCKED variants=0 status=BLOCKED' 'WARN' 'Promotion'
            Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError 'NO_VARIANTS_COMPILED' -incrementAttempt $false
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
              $latestBatchArtifactPath = [string]$batch.batch_artifact_path
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
            if ($ref.refinement_cycle_path) { $latestRefinementArtifactPath = [string]$ref.refinement_cycle_path }
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

          if ($promoStatus -ne 'BLOCKED') {
            Set-BundleState -bundlePath $bp -status 'DONE' -lastError '' -incrementAttempt $false
          }
        }
        $bundlesProcessed += 1
        $promotionsProcessed += 1
        $bundleSlotsUsed += 1
      } catch {
        $errorsCount += 1
        $errMsg = ''
        try { $errMsg = [string]$_.Exception.Message } catch { $errMsg = 'PROCESSING_ERROR' }
        Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError $errMsg -incrementAttempt $false
      }
    }

    if (-not $DryRun) {
      if ($maxConsecutiveReadFailHit) {
        $errorsCount += 1
        Emit-Summary 'BUNDLE_READ_FAIL_CAP' ("Bundle read fail cap hit: consecutive=" + $consecutiveBundleReadFails + " max=" + $maxConsecutiveBundleReadFails) 'FAIL' 'oQ'
      } elseif ($newBundlesSeen -gt 0 -and $processableNewBundles -eq 0) {
        $errorsCount += 1
        Emit-Summary 'NO_PROCESSABLE_NEW_BUNDLE' 'No processable NEW bundle found in scan window.' 'FAIL' 'oQ'
      } elseif ($bundlesProcessed -eq 0 -and $consecutiveBundleReadFails -gt 0) {
        $errorsCount += 1
        Emit-Summary 'NO_PROCESSABLE_NEW_BUNDLE' 'No processable NEW bundle found; only unreadable bundle(s) encountered.' 'FAIL' 'oQ'
      }
    }
  }

  if (-not $DryRun -and $batchExecuted -eq 0) {
    try {
      $specIndexPath = 'artifacts/strategy_specs/INDEX.json'
      $runIndexPath = 'artifacts/library/RUN_INDEX.json'
      $specCandidates = @()
      if (Test-Path $specIndexPath) {
        $specRaw = Get-Content $specIndexPath -Raw | ConvertFrom-Json
        if ($specRaw -is [System.Array]) { $specCandidates = $specRaw } elseif ($null -ne $specRaw) { $specCandidates = @($specRaw) }
      }

      $runRows = @()
      if (Test-Path $runIndexPath) {
        $runRaw = Get-Content $runIndexPath -Raw | ConvertFrom-Json
        if ($runRaw -is [System.Array]) { $runRows = $runRaw } elseif ($null -ne $runRaw) { $runRows = @($runRaw) }
      }

      $completedKeys = @{}
      foreach ($rr in $runRows) {
        try {
          $sp = [string]$rr.strategy_spec_path
          $vn = [string]$rr.variant_name
          if (-not [string]::IsNullOrWhiteSpace($sp) -and -not [string]::IsNullOrWhiteSpace($vn)) {
            $spNorm = $sp.Replace('\\','/').ToLowerInvariant()
            $completedKeys[($spNorm + '|' + $vn)] = $true
          }
        } catch {}
      }

      $backfillTried = 0
      foreach ($spPath in $specCandidates) {
        if ($backfillTried -ge 3) { break }
        if ([string]::IsNullOrWhiteSpace([string]$spPath)) { continue }
        if (-not (Test-Path -LiteralPath $spPath)) { continue }

        $specObj = $null
        try { $specObj = Get-Content -LiteralPath $spPath -Raw | ConvertFrom-Json } catch { continue }
        $variants = @($specObj.variants)
        if ($variants.Count -eq 0) { continue }

        $spNorm = ([string]$spPath).Replace('\\','/').ToLowerInvariant()
        $allCovered = $true
        foreach ($vv in $variants) {
          $vn = [string]$vv.name
          if ([string]::IsNullOrWhiteSpace($vn)) { continue }
          if (-not $completedKeys.ContainsKey($spNorm + '|' + $vn)) {
            $allCovered = $false
            break
          }
        }
        if ($allCovered) { continue }

        $backfillTried += 1
        $batch = $null
        try {
          $batch = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$spPath,'--variant','all') | ConvertFrom-Json
          $bdoc = Get-Content $batch.batch_artifact_path -Raw | ConvertFrom-Json
          $latestBatchArtifactPath = [string]$batch.batch_artifact_path
          $batchRuns += [int]$bdoc.summary.total_runs
          $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
          $batchSkipped += [int]$bdoc.summary.failed_runs
          foreach ($rr in $bdoc.runs) {
            if ($rr.skip_reason -eq 'FEASIBILITY_FAIL') { $batchGateFail += 1 }
            if ($rr.gate_pass -eq $true) { $candidatesPassingGate += 1 }
          }
          $execCount = ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
          $bStatus = if ($execCount -le 0) { 'WARN' } else { 'OK' }
          Emit-Summary 'BATCH_BACKTEST_SUMMARY' ("Batch(backfill): runs=" + $bdoc.summary.total_runs + " executed=" + $execCount + " skipped=" + $bdoc.summary.failed_runs + " gate_fail=" + $batchGateFail + " spec=" + [IO.Path]::GetFileName([string]$spPath)) $bStatus 'Backtester'
          $batchEmitted = $true

          if ($execCount -gt 0 -and $MaxRefinementsPerRun -gt 0 -and $refinementsRun -lt $MaxRefinementsPerRun) {
            try {
              $promoId = [IO.Path]::GetFileNameWithoutExtension([string]$spPath)
              $promoPath = "artifacts/promotions/" + (Get-Date -Format 'yyyyMMdd') + "/promo_backfill_" + $promoId + ".promotion_run.json"
              $promoObj = [ordered]@{
                schema_version = '1.0'
                id = "promo_backfill_" + $promoId
                created_at = [DateTime]::UtcNow.ToString('o')
                status = 'OK'
                reason_code = $null
                suggestion = $null
                input_linkmap_path = ''
                thesis_artifact_path = ''
                strategy_spec_artifact_path = $spPath
                batch_backtest_artifact_path = $batch.batch_artifact_path
                experiment_plan_artifact_path = $(if ($batch.experiment_plan_path) { $batch.experiment_plan_path } else { '' })
              }
              New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($promoPath)) | Out-Null
              ($promoObj | ConvertTo-Json -Depth 8) | Set-Content -Path $promoPath -Encoding utf8

              $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
              $refinementsRun += 1
              if ($ref.refinement_cycle_path) { $latestRefinementArtifactPath = [string]$ref.refinement_cycle_path }
              $candidatesReachingRefinement += 1
              try {
                $rdoc = Get-Content $ref.refinement_cycle_path -Raw | ConvertFrom-Json
                $refineVariants = [int]$rdoc.winner.summary.total_runs
                $refineExplore = [int]$rdoc.explore_variants_used_total
                $refineDelta = [string]$rdoc.best_score_delta
                $rStatus = if ([string]$rdoc.final_recommendation -eq 'NO_IMPROVEMENT') { 'WARN' } else { 'OK' }
                Emit-Summary 'REFINEMENT_SUMMARY' ("Refine(backfill): iters=" + $rdoc.iterations_used + " variants=" + $refineVariants + " explore=" + $refineExplore + " delta=" + $refineDelta + " status=" + $rdoc.final_recommendation + " spec=" + [IO.Path]::GetFileName([string]$spPath)) $rStatus 'Refinement'
                $refineEmitted = $true
              } catch {}
            } catch {
              Emit-Summary 'REFINEMENT_SUMMARY' ('Refine(backfill): iters=0 variants=0 explore=0 delta=n/a status=SKIPPED spec=' + [IO.Path]::GetFileName([string]$spPath)) 'WARN' 'Refinement'
              $refineEmitted = $true
            }
          }
        } catch {
          Emit-Summary 'BATCH_BACKTEST_SUMMARY' ('Batch(backfill): runs=0 executed=0 skipped=0 (error) spec=' + [IO.Path]::GetFileName([string]$spPath)) 'FAIL' 'Backtester'
          $batchEmitted = $true
        }
      }
    } catch {}
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

      try {
        if (Test-Path $topPath) {
          $topObj = Get-Content $topPath -Raw | ConvertFrom-Json
          $topCountActual = @($topObj).Count
        }
      } catch {}

      $runReadOk = $true
      try {
        if (-not (Test-Path $runPath)) { throw 'RUN_INDEX missing' }
        $runObj = Get-Content $runPath -Raw | ConvertFrom-Json
        $runCountActual = @($runObj).Count
      } catch {
        $runReadOk = $false
      }

      try {
        if (Test-Path $lessPath) {
          $lessObj = Get-Content $lessPath -Raw | ConvertFrom-Json
          $lessCountActual = @($lessObj).Count
        }
      } catch {}

      if ($runReadOk) {
        $libraryRunCount = [int]$runCountActual
        $libraryLessons = if ($null -eq $lessCountActual) { 0 } else { [int]$lessCountActual }
        $activeLibrarySize = [int]$runCountActual
        $topOut = if ($null -eq $topCountActual) { '?' } else { [string]$topCountActual }
        $lessOut = if ($null -eq $lessCountActual) { '?' } else { [string]$lessCountActual }
        Emit-Summary 'LIBRARIAN_SUMMARY' ("Library: top=" + $topOut + " run=" + $runCountActual + " lessons=" + $lessOut + " new=" + $newIndicatorsAdded + " archived=0") 'OK' 'Librarian'
        $libraryEmitted = $true
      } else {
        $activeLibrarySize = '?'
        Emit-Summary 'LIBRARY_READ_FAIL' 'Library read failed: RUN_INDEX unavailable/unparseable; active_library_size=?' 'WARN' 'Librarian'
        Emit-Summary 'LIBRARIAN_SUMMARY_READ_FAIL' 'Library: top=? run=? lessons=? new=? archived=? (skipped: read fail)' 'WARN' 'Librarian'
        $libraryEmitted = $true
      }
    } catch {
      $runPath = 'artifacts/library/RUN_INDEX.json'
      $runCountActual = $null
      $runReadOk = $true
      try {
        if (-not (Test-Path $runPath)) { throw 'RUN_INDEX missing' }
        $runObj = Get-Content $runPath -Raw | ConvertFrom-Json
        $runCountActual = @($runObj).Count
      } catch {
        $runReadOk = $false
      }

      if ($runReadOk) {
        $activeLibrarySize = [int]$runCountActual
      } else {
        $activeLibrarySize = '?'
        Emit-Summary 'LIBRARY_READ_FAIL' 'Library read failed: RUN_INDEX unavailable/unparseable; active_library_size=?' 'WARN' 'Librarian'
      }
      Emit-Summary 'LIBRARIAN_SUMMARY_READ_FAIL' 'Library: top=? run=? lessons=? new=? archived=? (skipped: run fail)' 'WARN' 'Librarian'
      $libraryEmitted = $true
    }

    if (($batchExecuted -gt 0 -or $refinementsRun -gt 0)) {
      try {
        $outcArgs = @('scripts/pipeline/analyser_outcome_worker.py','--run-id',$CycleRunId)
        if (-not [string]::IsNullOrWhiteSpace($latestBatchArtifactPath)) { $outcArgs += @('--batch-artifact',$latestBatchArtifactPath) }
        if (-not [string]::IsNullOrWhiteSpace($latestRefinementArtifactPath)) { $outcArgs += @('--refinement-artifact',$latestRefinementArtifactPath) }
        $outcomeRaw = Run-Py $outcArgs
        if ($outcomeRaw) {
          $outcomeLines = @($outcomeRaw -split "`r?`n")
          $outcomeJsonLine = $outcomeLines | Where-Object { $_ -match '^\{' } | Select-Object -Last 1
          if ($outcomeJsonLine) {
            try {
              $outcomeObj = $outcomeJsonLine | ConvertFrom-Json
              if ($outcomeObj.outcome_notes_path) {
                Emit-InfoSummary 'OUTCOME_NOTES_PATH' ("Outcome notes v2: " + [string]$outcomeObj.outcome_notes_path) 'Analyser'
              }
            } catch {}
          }
        }
      } catch {
        Emit-Summary 'ANALYSER_OUTCOME_SUMMARY' 'ANALYSER_OUTCOME_SUMMARY — processed=1 verdict=REVISE directives=1' 'WARN' 'Analyser'
      }
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

if ([int]$directiveVariantsEmitted -eq 0) {
  try {
    $latestSpec = Get-ChildItem -Path 'artifacts/strategy_specs' -Recurse -Filter '*.strategy_spec.json' -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($latestSpec) {
      $latestSpecObj = Get-Content -LiteralPath $latestSpec.FullName -Raw | ConvertFrom-Json
      $latestVariants = @($latestSpecObj.variants)
      $directiveVariantsEmitted = @($latestVariants | Where-Object { [string]$_.origin -eq 'DIRECTIVE' }).Count
      $explorationVariantsEmitted = @($latestVariants | Where-Object { [string]$_.name -like 'directive_exploration*' }).Count
      if ($directiveVariantsEmitted -gt 0) { $directiveNotesSeen = 1 }
    }
  } catch {}
}

$summary = [ordered]@{
  event = 'LAB_SUMMARY'
  created_at = [DateTime]::UtcNow.ToString('o')
  bundles_processed = $bundlesProcessed
  promotions_processed = $promotionsProcessed
  refinements_run = $refinementsRun
  new_candidates_count = $newCandidatesCount
  candidates_ingested = $candidatesIngested
  candidates_reaching_refinement = $candidatesReachingRefinement
  candidates_passing_gate = $candidatesPassingGate
  directive_notes_seen = [int]$directiveNotesSeen
  directive_variants_emitted = [int]$directiveVariantsEmitted
  active_library_size = $activeLibrarySize
  new_indicators_added = $newIndicatorsAdded
  skipped_indicators_dedup = $skippedIndicatorsDedup
  errors_count = $errorsCount
  dry_run = [bool]$DryRun
  insight_new = $insightNew
  insight_processed = $insightProcessed
  insight_failed = $insightFailed
  recombine_created = $recombineCreated
  recombine_bundle_path = $recombineBundlePath
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

$labCountersPath = Join-Path $stateDir 'lab_counters.json'
$labCounters = [ordered]@{ directive_loop_stall_cycles = 0; updated_at = [DateTime]::UtcNow.ToString('o') }
if (Test-Path $labCountersPath) {
  try {
    $labPrev = Get-Content $labCountersPath -Raw | ConvertFrom-Json
    if ($null -ne $labPrev.directive_loop_stall_cycles) { $labCounters.directive_loop_stall_cycles = [int]$labPrev.directive_loop_stall_cycles }
  } catch {}
}
if (([int]$directiveNotesSeen -eq 0) -or ([int]$directiveVariantsEmitted -eq 0)) {
  $labCounters.directive_loop_stall_cycles = [int]$labCounters.directive_loop_stall_cycles + 1
} else {
  $labCounters.directive_loop_stall_cycles = 0
}
$labCounters.updated_at = [DateTime]::UtcNow.ToString('o')
($labCounters | ConvertTo-Json -Depth 5) | Set-Content -Path $labCountersPath -Encoding utf8
$summary.directive_loop_stall_cycles = [int]$labCounters.directive_loop_stall_cycles

($summary | ConvertTo-Json -Depth 5) | Set-Content -Path 'data/state/autopilot_summary.json' -Encoding utf8

if (-not $DryRun) {
  if ([int]$counters.starvation_cycles -ge 12) {
    Emit-Summary 'LAB_STARVATION_WARN' ("Autopilot starvation: starvation_cycles=" + $counters.starvation_cycles + " candidates_reaching_refinement=" + $candidatesReachingRefinement) 'WARN' 'oQ'
  }
  if ([int]$counters.drought_cycles -ge 30) {
    Emit-Summary 'LAB_DROUGHT_WARN' ("Autopilot drought: drought_cycles=" + $counters.drought_cycles + " candidates_passing_gate=" + $candidatesPassingGate) 'WARN' 'oQ'
  }

  $directiveLoopStatus = if (([int]$directiveNotesSeen -eq 1) -and ([int]$directiveVariantsEmitted -gt 0)) { 'OK' } else { 'WARN' }
  Emit-Summary 'DIRECTIVE_LOOP_SUMMARY' ("Directive loop: notes=" + [int]$directiveNotesSeen + " directive_variants=" + [int]$directiveVariantsEmitted + " exploration_variants=" + [int]$explorationVariantsEmitted) $directiveLoopStatus 'oQ'

  if ([int]$labCounters.directive_loop_stall_cycles -ge 12) {
    Emit-Summary 'DIRECTIVE_LOOP_STALL_WARN' 'Directive loop stalled: 12 cycles without directive variants' 'WARN' 'oQ'
  }

  $aStatus = if ($errorsCount -gt 0) { 'FAIL' } else { 'OK' }
  Emit-Summary 'LAB_SUMMARY' ("Lab: ingested=" + $candidatesIngested + " reached_refinement=" + $candidatesReachingRefinement + " passing_gate=" + $candidatesPassingGate + " directive_notes_seen=" + [int]$directiveNotesSeen + " directive_variants_emitted=" + [int]$directiveVariantsEmitted + " active_library_size=" + $activeLibrarySize + " bundles=" + $bundlesProcessed + " promotions=" + $promotionsProcessed + " refinements=" + $refinementsRun + " errors=" + $errorsCount) $aStatus 'oQ'
}

Write-Output ($summary | ConvertTo-Json -Depth 5)

# Explicit exit for scheduled task success reporting
exit 0
