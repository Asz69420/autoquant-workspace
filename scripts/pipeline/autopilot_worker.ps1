param(
  [switch]$DryRun,
  [int]$MaxRefinementsPerRun = 1,
  [int]$MaxBundlesPerRun = 3,
  [switch]$RunYouTubeWatcher,
  [switch]$RunTVCatalogWorker,
  [switch]$ForceRecombine,
  [string]$FastCommand = '',
  [ValidateSet('WARN','FAIL')]
  [string]$RepoHygieneMode = 'FAIL',
  [switch]$SkipRepoHygieneGate
)

$ErrorActionPreference = 'Stop'
try { if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) { $PSNativeCommandUseErrorActionPreference = $false } } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $RepoRoot

$adaptivePolicyPath = Join-Path $RepoRoot 'config\adaptive_execution_policy.json'
$adaptiveGateScript = Join-Path $RepoRoot 'scripts\pipeline\evaluate_promotion_gate.py'
$adaptivePolicyEnabled = $false
try {
  if (Test-Path -LiteralPath $adaptivePolicyPath) {
    $adaptivePolicyObj = Get-Content -LiteralPath $adaptivePolicyPath -Raw | ConvertFrom-Json
    if ($adaptivePolicyObj -and $adaptivePolicyObj.enabled -and $adaptivePolicyObj.promotion_gate -and $adaptivePolicyObj.promotion_gate.enabled) {
      $adaptivePolicyEnabled = $true
    }
  }
} catch {
  $adaptivePolicyEnabled = $false
}

function Run-Py($pyArgs) {
  if ($DryRun) { return '' }

  $pinfo = New-Object System.Diagnostics.ProcessStartInfo
  $pinfo.FileName = 'python'
  $escaped = @()
  foreach ($a in @($pyArgs)) {
    $s = [string]$a
    $s = $s.Replace('"', '\"')
    $escaped += ('"' + $s + '"')
  }
  $pinfo.Arguments = ($escaped -join ' ')
  $pinfo.WorkingDirectory = $RepoRoot
  $pinfo.RedirectStandardOutput = $true
  $pinfo.RedirectStandardError = $true
  $pinfo.UseShellExecute = $false
  $pinfo.CreateNoWindow = $true
  try {
    $pinfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $pinfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8
  } catch {}

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $pinfo
  $p.Start() | Out-Null
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  if ($p.ExitCode -ne 0) {
    throw ("Python exit " + $p.ExitCode + ": " + $stderr)
  }

  return ([string]$stdout).Trim()
}

function Test-AutopilotProcessRunning([int]$ExcludePid = 0) {
  try {
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
      ($_.Name -match 'powershell') -and (
        ($_.CommandLine -match 'autopilot_worker\.ps1') -or
        ($_.CommandLine -match 'run_autopilot_task\.ps1')
      ) -and ($_.ProcessId -ne $ExcludePid)
    }
    return (@($procs).Count -gt 0)
  } catch {
    return $false
  }
}

function Ensure-Lock($name) {
  $lockDir = 'data/state/locks'
  if (-not (Test-Path $lockDir)) { New-Item -ItemType Directory -Path $lockDir | Out-Null }
  $lockPath = Join-Path $lockDir ($name + '.lock')
  $staleMinutes = 10
  if (Test-Path $lockPath) {
    $isStale = $false
    try {
      $raw = [string](Get-Content -Path $lockPath -Raw -ErrorAction Stop)
      $ts = [DateTime]::Parse($raw).ToUniversalTime()
      if (([DateTime]::UtcNow - $ts).TotalMinutes -ge $staleMinutes) { $isStale = $true }
    } catch {
      try {
        $item = Get-Item -LiteralPath $lockPath -ErrorAction Stop
        if (([DateTime]::UtcNow - $item.LastWriteTimeUtc).TotalMinutes -ge $staleMinutes) { $isStale = $true }
      } catch {}
    }
    if ($isStale) {
      if (-not (Test-AutopilotProcessRunning -ExcludePid $PID)) {
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
        Emit-Summary 'STALE_LOCK_CLEARED' ("Cleared stale lock: $lockPath age>=" + $staleMinutes + 'm and no autopilot process') 'WARN' 'Autopilot'
      } else {
        Emit-Summary 'STALE_LOCK_PRESERVED' ("Lock is stale but autopilot process appears active: $lockPath") 'INFO' 'Autopilot'
      }
    }
  }
  if (Test-Path $lockPath) { throw "Lock exists: $lockPath" }
  Set-Content -Path $lockPath -Value ([DateTime]::UtcNow.ToString('o')) -Encoding utf8
  return $lockPath
}

function Test-ValidJsonPath([object]$candidatePath) {
  if ($null -eq $candidatePath) { return $false }
  $p = [string]$candidatePath
  if ([string]::IsNullOrWhiteSpace($p)) { return $false }
  return (Test-Path -LiteralPath $p)
}

function Get-JsonPathFailDetail([string]$context, [object]$candidatePath) {
  $p = if ($null -eq $candidatePath) { '' } else { [string]$candidatePath }
  if ([string]::IsNullOrWhiteSpace($p)) {
    return ($context + ': missing batch_artifact_path in runner output')
  }
  if (-not (Test-Path -LiteralPath $p)) {
    return ($context + ': batch artifact path not found -> ' + $p)
  }
  return ($context + ': unknown json path error')
}

function Get-RecentBatchArtifactPath([datetime]$sinceUtc) {
  try {
    $root = 'artifacts/batches'
    if (-not (Test-Path -LiteralPath $root)) { return '' }
    $all = Get-ChildItem -Path $root -Recurse -Filter '*.batch_backtest.json' -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTimeUtc -Descending
    if ($null -eq $all -or @($all).Count -eq 0) { return '' }
    $cand = $null
    if ($sinceUtc -ne [datetime]::MinValue) {
      $cand = @($all | Where-Object { $_.LastWriteTimeUtc -ge $sinceUtc } | Select-Object -First 1)
    }
    if ($null -eq $cand -or @($cand).Count -eq 0) {
      $cand = @($all | Select-Object -First 1)
    }
    if ($cand -and $cand[0]) { return [string]$cand[0].FullName }
  } catch {}
  return ''
}

function Invoke-OutcomeWorker([string]$runId, [string]$batchArtifactPath, [string]$refinementArtifactPath = '') {
  if ([string]::IsNullOrWhiteSpace($batchArtifactPath)) {
    Emit-Summary 'OUTCOME_NOTES_MISSING' ('Outcome worker skipped: empty batch artifact path for run_id=' + $runId) 'WARN' 'Analyser'
    return ''
  }

  $batchPathNorm = [string]$batchArtifactPath
  $refPathNorm = [string]$refinementArtifactPath
  $outcomePathFromWorker = ''
  try {
    $outcArgs = @('scripts/pipeline/analyser_outcome_worker.py','--run-id',$runId,'--batch-artifact',$batchPathNorm)
    if (-not [string]::IsNullOrWhiteSpace($refPathNorm) -and (Test-Path -LiteralPath $refPathNorm)) {
      $outcArgs += @('--refinement-artifact',$refPathNorm)
    }
    $outcomeRaw = & python @outcArgs 2>&1
    $outcomeExit = $LASTEXITCODE
    if ($outcomeExit -ne 0) {
      $errText = if (-not [string]::IsNullOrWhiteSpace([string]$outcomeRaw)) { ([string]$outcomeRaw).Trim() } else { 'nonzero exit without output' }
      throw ("outcome worker exit=" + $outcomeExit + " output=" + $errText)
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$outcomeRaw)) {
      $outcomeLines = @($outcomeRaw -split "`r?`n")
      foreach ($ol in $outcomeLines) {
        if ($ol -like 'ANALYSER_OUTCOME_SUMMARY*') { Emit-Summary 'ANALYSER_OUTCOME_SUMMARY' $ol 'OK' 'Analyser' }
      }
      $outcomeJsonLine = $outcomeLines | Where-Object { $_ -match '^\{' } | Select-Object -Last 1
      if ($outcomeJsonLine) {
        try {
          $outcomeObj = $outcomeJsonLine | ConvertFrom-Json
          if ($outcomeObj.outcome_notes_path) {
            $outcomePathFromWorker = [string]$outcomeObj.outcome_notes_path
            Emit-InfoSummary 'OUTCOME_NOTES_PATH' ("Outcome notes v2: " + $outcomePathFromWorker) 'Analyser'
          }
        } catch {}
      }
    }
  } catch {
    $oe = 'outcome_worker_error'
    try { $oe = [string]$_.Exception.Message } catch {}
    Emit-Summary 'OUTCOME_WORKER_FAIL' ('Outcome worker failed: run_id=' + $runId + ' batch=' + $batchPathNorm + ' refinement=' + $refPathNorm + ' detail=' + $oe) 'FAIL' 'Analyser'
    return ''
  }

  $checked = @()
  if (-not [string]::IsNullOrWhiteSpace($outcomePathFromWorker)) { $checked += $outcomePathFromWorker }
  $todayDir = Join-Path 'artifacts/outcomes' (Get-Date -Format 'yyyyMMdd')
  $expectedPath = Join-Path $todayDir ('outcome_notes_' + $runId + '.json')
  $checked += $expectedPath
  $fallbackPattern = ('outcome_notes_' + $runId + '*.json')
  try {
    $fallback = Get-ChildItem -Path 'artifacts/outcomes' -Recurse -Filter $fallbackPattern -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($fallback) { $checked += [string]$fallback.FullName }
  } catch {}

  $found = $false
  foreach ($cp in $checked) {
    if (-not [string]::IsNullOrWhiteSpace([string]$cp) -and (Test-Path -LiteralPath ([string]$cp))) { $found = $true; break }
  }

  if (-not $found) {
    $checkedStr = if (@($checked).Count -gt 0) { (@($checked) -join '; ') } else { 'none' }
    Emit-Summary 'OUTCOME_NOTES_MISSING' ('Outcome worker invoked but notes missing: run_id=' + $runId + ' batch=' + $batchPathNorm + ' checked=' + $checkedStr) 'WARN' 'Analyser'
    return ''
  }

  foreach ($cp in $checked) {
    if (-not [string]::IsNullOrWhiteSpace([string]$cp) -and (Test-Path -LiteralPath ([string]$cp))) {
      return [string]$cp
    }
  }
  return ''
}

function Invoke-DirectiveDrivenSpecGeneration([string]$backfillSpecPath, [string]$outcomeNotePath) {
  if ([string]::IsNullOrWhiteSpace($backfillSpecPath) -or -not (Test-Path -LiteralPath $backfillSpecPath)) {
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: invalid backfill spec path=' + [string]$backfillSpecPath) 'FAIL' 'Strategist'
    return ''
  }
  if ([string]::IsNullOrWhiteSpace($outcomeNotePath) -or -not (Test-Path -LiteralPath $outcomeNotePath)) {
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: invalid outcome note path=' + [string]$outcomeNotePath) 'FAIL' 'Strategist'
    return ''
  }

  $outObj = $null
  try {
    $outObj = Get-Content -LiteralPath $outcomeNotePath -Raw | ConvertFrom-Json
  } catch {
    $msg = [string]$_.Exception.Message
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: outcome parse error detail=' + $msg) 'FAIL' 'Strategist'
    return ''
  }

  $verdict = [string]$outObj.verdict

  $hasDirectives = $false
  try {
    if ($outObj.directives -and @($outObj.directives).Count -gt 0) { $hasDirectives = $true }
  } catch {
    $msg = [string]$_.Exception.Message
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: directive read error detail=' + $msg) 'FAIL' 'Strategist'
    return ''
  }
  if (-not $hasDirectives) {
    Emit-Summary 'DIRECTIVE_GEN_DIAG' ('DIRECTIVE_GEN_DIAG verdict=' + $verdict + ' thesis_path=null emission_attempted=false') 'INFO' 'Strategist'
    return ''
  }

  Emit-Summary 'DIRECTIVE_GEN_DIAG' ('DIRECTIVE_GEN_DIAG verdict=' + $verdict + ' thesis_path=null emission_attempted=true') 'INFO' 'Strategist'

  $emitArgs = @('scripts/pipeline/emit_strategy_spec.py','--mode','directive-only','--source-spec',$backfillSpecPath,'--outcome-notes',$outcomeNotePath,'--generation-origin','directive-generated-from-backfill','--trigger-outcome-note',$outcomeNotePath,'--trigger-backfill-spec',$backfillSpecPath)
  Emit-Summary 'DIRECTIVE_GEN_DIAG' ('DIRECTIVE_GEN_DIAG verdict=' + $verdict + ' thesis_path=null emission_attempted=true cmd=python ' + ($emitArgs -join ' ')) 'INFO' 'Strategist'

  try {
    $prevNativeErrPref = $null
    try {
      if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
        $prevNativeErrPref = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
      }
    } catch {}

    $emitOut = ''
    $emitErr = ''
    $emitExit = -1

    function Invoke-DirectiveEmitterCapture([string[]]$argsList) {
      $psi = New-Object System.Diagnostics.ProcessStartInfo
      $psi.FileName = 'python'
      $escapedArgs = @()
      foreach ($arg in @($argsList)) {
        $sv = [string]$arg
        $sv = $sv.Replace('"', '\"')
        $escapedArgs += ('"' + $sv + '"')
      }
      $psi.Arguments = ($escapedArgs -join ' ')
      $psi.WorkingDirectory = $RepoRoot
      $psi.RedirectStandardOutput = $true
      $psi.RedirectStandardError = $true
      $psi.UseShellExecute = $false
      $psi.CreateNoWindow = $true
      try {
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
      } catch {}

      $proc = New-Object System.Diagnostics.Process
      $proc.StartInfo = $psi
      $proc.Start() | Out-Null
      $stdOutLocal = $proc.StandardOutput.ReadToEnd()
      $stdErrLocal = $proc.StandardError.ReadToEnd()
      $proc.WaitForExit()
      return [pscustomobject]@{ ExitCode = [int]$proc.ExitCode; StdOut = [string]$stdOutLocal; StdErr = [string]$stdErrLocal }
    }

    $emitResult = Invoke-DirectiveEmitterCapture $emitArgs
    $emitExit = [int]$emitResult.ExitCode
    $emitOut = [string]$emitResult.StdOut
    $emitErr = [string]$emitResult.StdErr
    $emitOutBytesB64 = ''
    $emitErrBytesB64 = ''
    try { $emitOutBytesB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($emitOut)) } catch { $emitOutBytesB64 = '' }
    try { $emitErrBytesB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($emitErr)) } catch { $emitErrBytesB64 = '' }
    Emit-Summary 'DIRECTIVE_GEN_RAW' ('DIRECTIVE_GEN_RAW exit=' + $emitExit + ' stdout_len=' + $emitOut.Length + ' stderr_len=' + $emitErr.Length + ' stdout=' + $emitOut + ' stderr=' + $emitErr + ' stdout_bytes_b64=' + $emitOutBytesB64 + ' stderr_bytes_b64=' + $emitErrBytesB64) 'INFO' 'Strategist'
    if ($emitExit -ne 0) {
      Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: nonzero exit=' + $emitExit + ' stdout=' + $emitOut + ' stderr=' + $emitErr) 'FAIL' 'Strategist'
      return ''
    }
    if (-not [string]::IsNullOrWhiteSpace($emitErr)) {
      Emit-Summary 'DIRECTIVE_GEN_STDERR_INFO' ('Directive generation stderr diagnostics (non-fatal): ' + $emitErr) 'INFO' 'Strategist'
    }
    if ([string]::IsNullOrWhiteSpace($emitOut)) {
      Emit-Summary 'DIRECTIVE_GEN_RETRY' 'Directive generation: empty strategist stdout on first attempt; retrying after 2s' 'WARN' 'Strategist'
      Start-Sleep -Seconds 2
      $emitResult = Invoke-DirectiveEmitterCapture $emitArgs
      $emitExit = [int]$emitResult.ExitCode
      $emitOut = [string]$emitResult.StdOut
      $emitErr = [string]$emitResult.StdErr
      if ($emitExit -ne 0 -or [string]::IsNullOrWhiteSpace($emitOut)) {
        Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: empty strategist stdout after retry exit=' + $emitExit + ' stdout=' + $emitOut + ' stderr=' + $emitErr) 'FAIL' 'Strategist'
        return ''
      }
      if (-not [string]::IsNullOrWhiteSpace($emitErr)) {
        Emit-Summary 'DIRECTIVE_GEN_STDERR_INFO' ('Directive generation stderr diagnostics after retry (non-fatal): ' + $emitErr) 'INFO' 'Strategist'
      }
    }
    $emitObj = $null
    try {
      # Robust parsing: emitter may print advisory/non-JSON lines before final JSON.
      $emitLines = @([string]$emitOut -split "`r?`n") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
      for ($i = $emitLines.Count - 1; $i -ge 0; $i--) {
        $candidate = ([string]$emitLines[$i]).Trim()
        if (-not ($candidate.StartsWith('{') -or $candidate.StartsWith('['))) { continue }
        try {
          $emitObj = $candidate | ConvertFrom-Json
          break
        } catch {}
      }
      if ($null -eq $emitObj) {
        # Fallback 1: extract trailing JSON object/array from mixed single-line output
        $objIdx = ([string]$emitOut).LastIndexOf('{')
        if ($objIdx -ge 0) {
          $tailObj = ([string]$emitOut).Substring($objIdx).Trim()
          if (-not [string]::IsNullOrWhiteSpace($tailObj)) {
            try { $emitObj = $tailObj | ConvertFrom-Json } catch {}
          }
        }
        if ($null -eq $emitObj) {
          $arrIdx = ([string]$emitOut).LastIndexOf('[')
          if ($arrIdx -ge 0) {
            $tailArr = ([string]$emitOut).Substring($arrIdx).Trim()
            if (-not [string]::IsNullOrWhiteSpace($tailArr)) {
              try { $emitObj = $tailArr | ConvertFrom-Json } catch {}
            }
          }
        }
      }
      if ($null -eq $emitObj) {
        # Fallback 2: try full payload for compatibility with pure-JSON output
        $emitObj = $emitOut | ConvertFrom-Json
      }
    } catch {
      Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: parse error exit=' + $emitExit + ' stdout=' + $emitOut + ' stderr=' + $emitErr) 'FAIL' 'Strategist'
      return ''
    }

    $generatedSpecPath = [string]$emitObj.strategy_spec_path
    if (-not [string]::IsNullOrWhiteSpace($generatedSpecPath)) {
      Emit-Summary 'DIRECTIVE_BACKFILL_GENERATION' ('Directive generation from backfill: verdict=' + $verdict + ' directives=' + @($outObj.directives).Count + ' generated_spec=' + [IO.Path]::GetFileName([string]$generatedSpecPath) + ' deferred_to_next_cycle=true') 'OK' 'Strategist'
      return $generatedSpecPath
    }
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: strategist returned no strategy_spec_path exit=' + $emitExit + ' stdout=' + $emitOut + ' stderr=' + $emitErr) 'FAIL' 'Strategist'
  } catch {
    $msg = [string]$_.Exception.Message
    Emit-Summary 'DIRECTIVE_GEN_FAIL' ('Directive generation fail: emission error detail=' + $msg + ' stdout=' + [string]$emitOut + ' stderr=' + [string]$emitErr) 'FAIL' 'Strategist'
  }

  return ''
}

function Resolve-SpecFamilyKey([string]$specPath, [hashtable]$cache) {
  if ([string]::IsNullOrWhiteSpace($specPath)) { return 'unknown' }
  $norm = $specPath.Replace('\\','/').ToLowerInvariant()
  if ($cache.ContainsKey($norm)) { return [string]$cache[$norm] }

  $resolved = $specPath
  if (-not (Test-Path -LiteralPath $resolved)) {
    try {
      $candidate = Join-Path (Get-Location) $specPath
      if (Test-Path -LiteralPath $candidate) { $resolved = $candidate }
    } catch {}
  }
  if (-not (Test-Path -LiteralPath $resolved)) {
    $cache[$norm] = 'unknown'
    return 'unknown'
  }

  try {
    $obj = Get-Content -LiteralPath $resolved -Raw | ConvertFrom-Json
    $th = [string]$obj.source_thesis_path
    if (-not [string]::IsNullOrWhiteSpace($th)) {
      $fam = [IO.Path]::GetFileNameWithoutExtension([IO.Path]::GetFileNameWithoutExtension($th))
      if (-not [string]::IsNullOrWhiteSpace($fam)) { $cache[$norm] = $fam; return $fam }
    }
    $src = [string]$obj.source_spec_path
    if (-not [string]::IsNullOrWhiteSpace($src)) {
      $fam = Resolve-SpecFamilyKey $src $cache
      if (-not [string]::IsNullOrWhiteSpace($fam)) { $cache[$norm] = $fam; return $fam }
    }
    $sid = [string]$obj.id
    if (-not [string]::IsNullOrWhiteSpace($sid)) { $cache[$norm] = $sid; return $sid }
  } catch {}

  $cache[$norm] = 'unknown'
  return 'unknown'
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
$countedBatchArtifacts = @{}
$usedBackfillSpecs = @()
$backfillOutcomeQueue = @()
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
$directiveBackfillSpecsGenerated = 0
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
$latestStrategySpecPath = ''

if (Handle-FastCommand $FastCommand) {
  exit 0
}

try {
  if (-not $DryRun -and -not $SkipRepoHygieneGate) {
    $hygieneScript = Join-Path $RepoRoot 'scripts\automation\repo_hygiene_gate.ps1'
    if (Test-Path -LiteralPath $hygieneScript) {
      $hOut = @()
      & powershell -NoProfile -ExecutionPolicy Bypass -File $hygieneScript -Mode $RepoHygieneMode -LockStaleMinutes 60 -NoBanner 2>&1 | ForEach-Object { $hOut += [string]$_ }
      $hExit = $LASTEXITCODE
      $hText = ($hOut -join ' | ')
      if ([string]::IsNullOrWhiteSpace($hText)) { $hText = 'repo hygiene gate completed (no output)' }
      if ($hExit -ne 0) {
        Emit-Summary 'REPO_HYGIENE_GATE' ('Repo hygiene gate exit=' + $hExit + ' mode=' + $RepoHygieneMode + ' details=' + $hText) 'WARN' 'Autopilot'
        if ($RepoHygieneMode -eq 'FAIL') {
          throw ('REPO_HYGIENE_GATE_FAIL mode=FAIL exit=' + $hExit)
        }
      } else {
        Emit-Summary 'REPO_HYGIENE_GATE' ('Repo hygiene gate mode=' + $RepoHygieneMode + ' status=OK details=' + $hText) 'INFO' 'Autopilot'
      }
    } else {
      Emit-Summary 'REPO_HYGIENE_GATE' ('Repo hygiene script missing: ' + $hygieneScript) 'WARN' 'Autopilot'
    }
  }

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
  $bundlePaths = @()
  try {
    $allBundleFiles = Get-ChildItem -Path 'artifacts/bundles' -Recurse -Filter '*.bundle.json' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending
    $bundlePaths = @($allBundleFiles | ForEach-Object { [string]$_.FullName })
    if (-not $DryRun) {
      if (-not (Test-Path -LiteralPath 'artifacts/bundles')) { New-Item -ItemType Directory -Path 'artifacts/bundles' -Force | Out-Null }
      $rootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\\..'))
      $bundleIndexOut = @($bundlePaths | ForEach-Object {
        $full = [IO.Path]::GetFullPath([string]$_)
        if ($full.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
          return (($full.Substring($rootPath.Length)).TrimStart('\','/') -replace '\\','/')
        }
        return ([string]$_ -replace '\\','/')
      })
      ($bundleIndexOut | ConvertTo-Json -Depth 3) | Set-Content -LiteralPath $bundleIndexPath -Encoding utf8
      $bundlePaths = @($bundleIndexOut)
    }
  } catch {
    $bundlePaths = @()
  }

  if (Test-Path $bundleIndexPath) {
    if ($bundlePaths.Count -eq 0) {
      try {
        $tmpBundlePaths = Get-Content $bundleIndexPath -Raw | ConvertFrom-Json
        if ($tmpBundlePaths -is [System.Array]) { $bundlePaths = $tmpBundlePaths } elseif ($null -ne $tmpBundlePaths) { $bundlePaths = @($tmpBundlePaths) } else { $bundlePaths = @() }
      } catch { $bundlePaths = @() }
    }

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

    $newCandidates = @()
    foreach ($cand in @($bundlePaths)) {
      try {
        if (-not (Test-Path -LiteralPath $cand)) { continue }
        $cb = Get-Content -LiteralPath $cand -Raw | ConvertFrom-Json
        $cs = [string]$cb.status
        if ([string]::IsNullOrWhiteSpace($cs)) { $cs = 'NEW' }
        if ($cs -eq 'NEW') { $newCandidates += [string]$cand }
      } catch {}
    }
    $selected = if (@($bundlePaths).Count -gt 0) { [string]$bundlePaths[0] } else { '' }
    Emit-Summary 'BUNDLE_SELECT_DIAG' ('Bundle select: new_count=' + [string]@($newCandidates).Count + ' selected=' + $selected + ' new_paths=' + ((@($newCandidates) -join ';'))) 'INFO' 'Autopilot'

    Emit-Summary 'BUNDLE_SCAN_DIAG' ('Bundle scan: index_exists=' + (Test-Path $bundleIndexPath) + ' paths=' + [string]@($bundlePaths).Count) 'INFO' 'Autopilot'
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
        Emit-Summary 'BUNDLE_PROCESS_START' ('Bundle process start: path=' + [string]$bp + ' status=' + $bundleStatus) 'INFO' 'Autopilot'

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

          $an = $null
          $anRaw = ''
          $thesisPath = ''
          try {
            $anArgs = @('scripts/pipeline/run_analyser.py','--research-card-path',$b.research_card_path)
            if (-not [string]::IsNullOrWhiteSpace([string]$lm)) { $anArgs += @('--linkmap-path',$lm) }
            $anRaw = Run-Py $anArgs
            try {
              $an = $anRaw | ConvertFrom-Json
            } catch {
              $parseMsg = 'unknown_parse_error'
              try { $parseMsg = [string]$_.Exception.Message } catch {}
              Emit-Summary 'THESIS_GEN_FAIL' ('THESIS_GEN_FAIL stage=run_analyser parse=json detail=' + $parseMsg + ' stdout=' + [string]$anRaw) 'FAIL' 'Analyser'
              throw
            }

            $thesisPath = [string]$an.thesis_path
            if ([string]::IsNullOrWhiteSpace($thesisPath)) { $thesisPath = [string]$an.thesis_artifact_path }
            if ([string]::IsNullOrWhiteSpace($thesisPath)) { $thesisPath = [string]$an.thesis }

            if ([string]::IsNullOrWhiteSpace($thesisPath)) {
              Emit-Summary 'BUNDLE_THESIS_RESULT' ('Bundle thesis result: path=' + [string]$bp + ' thesis_path=<empty>') 'FAIL' 'Analyser'
              Emit-Summary 'THESIS_GEN_FAIL' ('THESIS_GEN_FAIL stage=run_analyser reason=EMPTY_THESIS_PATH stdout=' + [string]$anRaw) 'FAIL' 'Analyser'
              Emit-Summary 'SPEC_EMIT_BLOCKED' 'empty thesis path from analyser' 'WARN' 'Strategist'
              Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=OK spec=BLOCKED variants=0 status=BLOCKED' 'WARN' 'Promotion'
              Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError 'EMPTY_THESIS_PATH_FROM_ANALYSER' -incrementAttempt $false
              $promotionEmitted = $true
              Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: blocked promotion)' 'WARN' 'Backtester'
              $batchEmitted = $true
              Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'OK' 'Refinement'
              $refineEmitted = $true
              $bundlesProcessed += 1
              $bundleSlotsUsed += 1
              continue
            }
          } catch {
            $thesisErr = 'run_analyser_error'
            try { $thesisErr = [string]$_.Exception.Message } catch {}
            Emit-Summary 'BUNDLE_THESIS_RESULT' ('Bundle thesis result: path=' + [string]$bp + ' thesis_path=<error> detail=' + $thesisErr) 'FAIL' 'Analyser'
            Emit-Summary 'THESIS_GEN_FAIL' ('THESIS_GEN_FAIL stage=run_analyser detail=' + $thesisErr + ' research_card=' + [string]$b.research_card_path + ' linkmap=' + [string]$lm) 'FAIL' 'Analyser'
            Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError ('THESIS_GEN_FAIL: ' + $thesisErr) -incrementAttempt $false
            Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=BLOCKED spec=SKIPPED variants=0 status=BLOCKED reason=THESIS_GEN_FAIL' 'FAIL' 'Promotion'
            $promotionEmitted = $true
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: thesis generation failed)' 'WARN' 'Backtester'
            $batchEmitted = $true
            Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED (THESIS_GEN_FAIL)' 'WARN' 'Refinement'
            $refineEmitted = $true
            $bundlesProcessed += 1
            $bundleSlotsUsed += 1
            continue
          }

          Emit-Summary 'BUNDLE_THESIS_RESULT' ('Bundle thesis result: path=' + [string]$bp + ' thesis_path=' + [string]$thesisPath) 'OK' 'Analyser'
          Run-Py @('scripts/pipeline/verify_pipeline_stage2.py','--thesis',$thesisPath) | Out-Null
          $specEmitArgs = @('scripts/pipeline/emit_strategy_spec.py','--thesis-path',$thesisPath)
          Emit-Summary 'SPEC_EMIT_DIAG' ('SPEC_EMIT_DIAG cmd=python ' + ($specEmitArgs -join ' ')) 'INFO' 'Strategist'
          $sp = Run-Py $specEmitArgs | ConvertFrom-Json
          if ($sp.strategy_spec_path) { $latestStrategySpecPath = [string]$sp.strategy_spec_path }
          $variantCount = 0
          if ($sp.variants) { $variantCount = [int]$sp.variants }
          Emit-Summary 'BUNDLE_SPEC_RESULT' ('Bundle spec result: path=' + [string]$bp + ' spec_status=' + [string]$sp.status + ' variants=' + [string]$variantCount + ' spec_path=' + [string]$sp.strategy_spec_path) 'INFO' 'Strategist'

          try {
            if ($sp.strategy_spec_path -and (Test-Path -LiteralPath $sp.strategy_spec_path)) {
              $specObj = Get-Content -LiteralPath $sp.strategy_spec_path -Raw | ConvertFrom-Json
              $specVariants = @($specObj.variants)
              $specIsDirectiveContext = (-not [string]::IsNullOrWhiteSpace([string]$specObj.source_outcome_notes_path)) -or ([string]$specObj.generation_origin -like 'directive-generated*')
              $directiveBatch = @($specVariants | Where-Object {
                $origin = [string]$_.origin
                ($origin -eq 'DIRECTIVE') -or ($specIsDirectiveContext -and $origin -eq 'DIVERSITY')
              }).Count
              $explorationBatch = @($specVariants | Where-Object { [string]$_.name -like 'directive_exploration*' }).Count
              if ($directiveBatch -gt 0) { $directiveNotesSeen = 1 }
              $directiveVariantsEmitted += [int]$directiveBatch
              $explorationVariantsEmitted += [int]$explorationBatch
            }
          } catch {}

          $promoStatus = 'OK'
          $promoBlockedByAdaptiveGate = $false
          if ($sp.status -and [string]$sp.status -eq 'BLOCKED') { $promoStatus = 'BLOCKED' }
          if ($variantCount -eq 0) { $promoStatus = 'BLOCKED' }

          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'PROMOTION_SUMMARY' 'Promote: bundles=1 thesis=OK spec=BLOCKED variants=0 status=BLOCKED' 'WARN' 'Promotion'
            Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError 'NO_VARIANTS_COMPILED' -incrementAttempt $false
          } else {
            Emit-Summary 'PROMOTION_SUMMARY' ("Promote: bundles=1 thesis=OK spec=OK variants=" + $variantCount + " status=OK") 'OK' 'Promotion'
          }
          $promotionEmitted = $true
          $bundlesProcessed += 1
          if ($promoStatus -ne 'BLOCKED') { $promotionsProcessed += 1 }
          $bundleSlotsUsed += 1

          $batch = $null
          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: blocked promotion)' 'WARN' 'Backtester'
            $batchEmitted = $true
          } elseif ($variantCount -eq 0) {
            Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'OK' 'Backtester'
            $batchEmitted = $true
          } else {
            try {
              $batchStartUtc = [DateTime]::UtcNow.AddMinutes(-1)
              # Balrog pre-backtest gate
              $balrogResult = powershell -ExecutionPolicy Bypass -File "$RepoRoot\scripts\pipeline\balrog_gate.ps1" -Mode "pre-backtest"
              if ($LASTEXITCODE -ne 0) {
                # Safety: fail closed when Balrog pre-gate blocks so backtests do not run on flagged artifacts.
                throw ("BALROG BLOCKED: Pre-backtest gate failed. " + [string]$balrogResult)
              }
              $batchRaw = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$sp.strategy_spec_path,'--variant','all')
              # Balrog post-backtest verification
              powershell -ExecutionPolicy Bypass -File "$RepoRoot\scripts\pipeline\balrog_gate.ps1" -Mode "post-backtest"
              if ([string]::IsNullOrWhiteSpace([string]$batchRaw)) {
                throw 'promotion batch: empty runner output'
              }
              $batch = $batchRaw | ConvertFrom-Json
              $batchArtifactPath = [string]$batch.batch_artifact_path
              if (-not (Test-ValidJsonPath $batchArtifactPath)) {
                $fallbackPath = Get-RecentBatchArtifactPath $batchStartUtc
                if (-not (Test-ValidJsonPath $fallbackPath)) {
                  $fallbackPath = Get-RecentBatchArtifactPath ([datetime]::MinValue)
                }
                if (Test-ValidJsonPath $fallbackPath) {
                  $batchArtifactPath = $fallbackPath
                } else {
                  throw (Get-JsonPathFailDetail 'promotion batch' $batch.batch_artifact_path)
                }
              }
              $bdoc = Get-Content -LiteralPath $batchArtifactPath -Raw | ConvertFrom-Json
              $latestBatchArtifactPath = [string]$batchArtifactPath
              $batchRuns += [int]$bdoc.summary.total_runs
              $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
              $batchSkipped += [int]$bdoc.summary.failed_runs
              $batchGateFailThis = @($bdoc.runs | Where-Object { [string]$_.skip_reason -eq 'FEASIBILITY_FAIL' }).Count
              $gatePassThis = @($bdoc.runs | Where-Object { $_.gate_pass -eq $true }).Count
              if (-not $countedBatchArtifacts.ContainsKey([string]$batchArtifactPath)) {
                $countedBatchArtifacts[[string]$batchArtifactPath] = $true
                $batchGateFail += [int]$batchGateFailThis
                $candidatesPassingGate += [int]$gatePassThis
              }
              $execCount = ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
              $bStatus = if ($execCount -le 0) { 'WARN' } else { 'OK' }
              Emit-Summary 'BATCH_BACKTEST_SUMMARY' ("Batch: runs=" + $bdoc.summary.total_runs + " executed=" + $execCount + " skipped=" + $bdoc.summary.failed_runs + " gate_fail=" + $batchGateFailThis + " gate_pass=" + $gatePassThis) $bStatus 'Backtester'
              $batchEmitted = $true
            } catch {
              $batchErr = 'batch_error'
              try { $batchErr = [string]$_.Exception.Message } catch {}
              Emit-Summary 'BATCH_BACKTEST_SUMMARY' ('Batch: runs=0 executed=0 skipped=0 (error) detail=' + $batchErr) 'FAIL' 'Backtester'
              $batchEmitted = $true
            }
          }

          if ($promoStatus -ne 'BLOCKED' -and $adaptivePolicyEnabled -and (Test-Path -LiteralPath $adaptiveGateScript)) {
            try {
              $gateBatchPath = ''
              if ($null -ne $batchArtifactPath -and -not [string]::IsNullOrWhiteSpace([string]$batchArtifactPath)) {
                $gateBatchPath = [string]$batchArtifactPath
              }
              if (-not [string]::IsNullOrWhiteSpace($gateBatchPath) -and (Test-Path -LiteralPath $gateBatchPath)) {
                $gateRaw = Run-Py @('scripts/pipeline/evaluate_promotion_gate.py','--batch-artifact',$gateBatchPath,'--policy',$adaptivePolicyPath)
                if (-not [string]::IsNullOrWhiteSpace([string]$gateRaw)) {
                  $gateObj = $gateRaw | ConvertFrom-Json
                  $gateStatus = [string]$gateObj.status
                  $gateSummary = [string]$gateObj.summary
                  if ($gateStatus -eq 'BLOCKED') {
                    $promoStatus = 'BLOCKED'
                    $promoBlockedByAdaptiveGate = $true
                    Emit-Summary 'PROMOTION_ADAPTIVE_GATE' $gateSummary 'WARN' 'Promotion'
                    Set-BundleState -bundlePath $bp -status 'BLOCKED' -lastError 'ADAPTIVE_PROMOTION_GATE' -incrementAttempt $false
                  } else {
                    Emit-InfoSummary 'PROMOTION_ADAPTIVE_GATE' $gateSummary 'Promotion'
                  }
                }
              }
            } catch {
              $gateErr = [string]$_.Exception.Message
              Emit-Summary 'PROMOTION_ADAPTIVE_GATE' ('adaptive gate error: ' + $gateErr) 'WARN' 'Promotion'
            }
          }

          $promoId = [IO.Path]::GetFileNameWithoutExtension($sp.strategy_spec_path)
          $promoPath = "artifacts/promotions/" + (Get-Date -Format 'yyyyMMdd') + "/promo_" + $promoId + ".promotion_run.json"
          $promoReasonCode = $null
          $promoSuggestion = $null
          if ($promoStatus -eq 'BLOCKED') {
            if ($promoBlockedByAdaptiveGate) {
              $promoReasonCode = 'ADAPTIVE_PROMOTION_GATE'
              $promoSuggestion = 'Quality gate blocked promotion; improve PF / DD / expectancy before retry.'
            } else {
              $promoReasonCode = 'NO_VARIANTS_COMPILED'
              $promoSuggestion = 'Indicator not mapped to executable signals yet; needs rule extraction or builtin mapping.'
            }
          }
          $promoObj = [ordered]@{
            schema_version = '1.0'
            id = "promo_" + $promoId
            created_at = [DateTime]::UtcNow.ToString('o')
            status = $(if ($promoStatus -eq 'BLOCKED') { 'BLOCKED' } else { 'OK' })
            reason_code = $promoReasonCode
            suggestion = $promoSuggestion
            input_linkmap_path = $lm
            thesis_artifact_path = $an.thesis_path
            strategy_spec_artifact_path = $sp.strategy_spec_path
            batch_backtest_artifact_path = $(if ($null -ne $batchArtifactPath -and -not [string]::IsNullOrWhiteSpace([string]$batchArtifactPath)) { $batchArtifactPath } elseif ($null -ne $batch) { $batch.batch_artifact_path } else { '' })
            experiment_plan_artifact_path = $(if ($null -ne $batch) { $batch.experiment_plan_path } else { '' })
          }
          New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($promoPath)) | Out-Null
          ($promoObj | ConvertTo-Json -Depth 8) | Set-Content -Path $promoPath -Encoding utf8

          if ($promoStatus -eq 'BLOCKED') {
            Emit-Summary 'REFINEMENT_SUMMARY' 'Refine: iters=0 variants=0 explore=0 delta=n/a status=SKIPPED' 'OK' 'Refinement'
            $refineEmitted = $true
          } elseif ($MaxRefinementsPerRun -gt 0 -and $refinementsRun -lt $MaxRefinementsPerRun) {
            $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
            $refPath = [string]$ref.refinement_cycle_path
            if (-not [string]::IsNullOrWhiteSpace($refPath) -and (Test-Path -LiteralPath $refPath)) {
              $refinementsRun += 1
              $latestRefinementArtifactPath = $refPath
              $candidatesReachingRefinement += 1
            }
            try {
              if (-not (Test-Path -LiteralPath $refPath)) { throw 'REFINEMENT_ARTIFACT_MISSING' }
              $rdoc = Get-Content -LiteralPath $refPath -Raw | ConvertFrom-Json
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

  if (-not $DryRun) {
    Emit-Summary 'BACKFILL_DIAG' ('Entered backfill block checkpoint: batchExecuted=' + [string]$batchExecuted + ' bundlesProcessed=' + [string]$bundlesProcessed + ' batchEmitted=' + [string]$batchEmitted) 'OK' 'Autopilot'
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

      $recentBackfillSpecs = @()
      $labCountersPathRead = Join-Path 'data/state' 'lab_counters.json'
      if (Test-Path $labCountersPathRead) {
        try {
          $labStateRead = Get-Content $labCountersPathRead -Raw | ConvertFrom-Json
          if ($labStateRead.recent_backfill_specs) {
            $recentBackfillSpecs = @($labStateRead.recent_backfill_specs | ForEach-Object { [string]$_ })
          }
        } catch {}
      }

      $completedKeys = @{}
      $familyCache = @{}
      $familyBestPf = @{}
      foreach ($rr in $runRows) {
        try {
          $sp = [string]$rr.strategy_spec_path
          $vn = [string]$rr.variant_name
          if (-not [string]::IsNullOrWhiteSpace($sp) -and -not [string]::IsNullOrWhiteSpace($vn)) {
            $spNorm = $sp.Replace('\\','/').ToLowerInvariant()
            $completedKeys[($spNorm + '|' + $vn)] = $true
          }

          $pf = 0.0
          try { $pf = [double]$rr.profit_factor } catch { $pf = 0.0 }
          if (-not [string]::IsNullOrWhiteSpace($sp)) {
            $fam = Resolve-SpecFamilyKey $sp $familyCache
            if (-not $familyBestPf.ContainsKey($fam) -or $pf -gt [double]$familyBestPf[$fam]) {
              $familyBestPf[$fam] = [double]$pf
            }
          }
        } catch {}
      }

      $orderedSpecCandidates = @()
      foreach ($spPathCand in $specCandidates) {
        if ([string]::IsNullOrWhiteSpace([string]$spPathCand)) { continue }
        if (-not (Test-Path -LiteralPath $spPathCand)) { continue }
        try {
          $fi = Get-Item -LiteralPath $spPathCand -ErrorAction Stop
          $fam = Resolve-SpecFamilyKey ([string]$spPathCand) $familyCache
          $famBest = -1.0
          if ($familyBestPf.ContainsKey($fam)) { $famBest = [double]$familyBestPf[$fam] }
          $orderedSpecCandidates += [pscustomobject]@{ path = [string]$spPathCand; family = [string]$fam; family_best_pf = [double]$famBest; mtime = $fi.LastWriteTimeUtc }
        } catch {}
      }
      $orderedSpecCandidates = @($orderedSpecCandidates | Sort-Object @{Expression='family_best_pf';Descending=$true}, @{Expression='mtime';Descending=$true})

      $backfillTried = 0
      foreach ($specEntry in $orderedSpecCandidates) {
        if ($backfillTried -ge 3) { break }
        $spPath = [string]$specEntry.path
        if ($recentBackfillSpecs -contains $spPath) { continue }

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
        $usedBackfillSpecs += $spPath
        $latestStrategySpecPath = [string]$spPath
        $batch = $null
        try {
          $batchStartUtc = [DateTime]::UtcNow.AddMinutes(-1)
          # Balrog pre-backtest gate
          $balrogResult = powershell -ExecutionPolicy Bypass -File "$RepoRoot\scripts\pipeline\balrog_gate.ps1" -Mode "pre-backtest"
          if ($LASTEXITCODE -ne 0) {
            # Safety: fail closed when Balrog pre-gate blocks so backtests do not run on flagged artifacts.
            throw ("BALROG BLOCKED: Pre-backtest gate failed. " + [string]$balrogResult)
          }
          $batchRaw = Run-Py @('scripts/pipeline/run_batch_backtests.py','--strategy-spec',$spPath,'--variant','all')
          # Balrog post-backtest verification
          powershell -ExecutionPolicy Bypass -File "$RepoRoot\scripts\pipeline\balrog_gate.ps1" -Mode "post-backtest"
          if ([string]::IsNullOrWhiteSpace([string]$batchRaw)) {
            throw ('backfill spec=' + [IO.Path]::GetFileName([string]$spPath) + ': empty runner output')
          }
          $batch = $batchRaw | ConvertFrom-Json
          $batchArtifactPath = [string]$batch.batch_artifact_path
          if (-not (Test-ValidJsonPath $batchArtifactPath)) {
            $fallbackPath = Get-RecentBatchArtifactPath $batchStartUtc
            if (-not (Test-ValidJsonPath $fallbackPath)) {
              $fallbackPath = Get-RecentBatchArtifactPath ([datetime]::MinValue)
            }
            if (Test-ValidJsonPath $fallbackPath) {
              $batchArtifactPath = $fallbackPath
            } else {
              throw (Get-JsonPathFailDetail ('backfill spec=' + [IO.Path]::GetFileName([string]$spPath)) $batch.batch_artifact_path)
            }
          }
          $bdoc = Get-Content -LiteralPath $batchArtifactPath -Raw | ConvertFrom-Json
          $latestBatchArtifactPath = [string]$batchArtifactPath
          $batchRuns += [int]$bdoc.summary.total_runs
          $batchExecuted += ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
          $batchSkipped += [int]$bdoc.summary.failed_runs
          $batchGateFailThis = @($bdoc.runs | Where-Object { [string]$_.skip_reason -eq 'FEASIBILITY_FAIL' }).Count
          $gatePassThis = @($bdoc.runs | Where-Object { $_.gate_pass -eq $true }).Count
          if (-not $countedBatchArtifacts.ContainsKey([string]$batchArtifactPath)) {
            $countedBatchArtifacts[[string]$batchArtifactPath] = $true
            $batchGateFail += [int]$batchGateFailThis
            $candidatesPassingGate += [int]$gatePassThis
          }
          $execCount = ([int]$bdoc.summary.total_runs - [int]$bdoc.summary.failed_runs)
          $bStatus = if ($execCount -le 0) { 'WARN' } else { 'OK' }
          Emit-Summary 'BATCH_BACKTEST_SUMMARY' ("Batch(backfill): runs=" + $bdoc.summary.total_runs + " executed=" + $execCount + " skipped=" + $bdoc.summary.failed_runs + " gate_fail=" + $batchGateFailThis + " gate_pass=" + $gatePassThis + " spec=" + [IO.Path]::GetFileName([string]$spPath)) $bStatus 'Backtester'
          $batchEmitted = $true

          $backfillRefPath = ''
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
                batch_backtest_artifact_path = $batchArtifactPath
                experiment_plan_artifact_path = $(if ($batch.experiment_plan_path) { $batch.experiment_plan_path } else { '' })
              }
              New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($promoPath)) | Out-Null
              ($promoObj | ConvertTo-Json -Depth 8) | Set-Content -Path $promoPath -Encoding utf8

              $ref = Run-Py @('scripts/pipeline/run_refinement_loop.py','--promotion-run',$promoPath,'--max-iters','1') | ConvertFrom-Json
              $refPath = [string]$ref.refinement_cycle_path
              if (-not [string]::IsNullOrWhiteSpace($refPath) -and (Test-Path -LiteralPath $refPath)) {
                $refinementsRun += 1
                $latestRefinementArtifactPath = $refPath
                $backfillRefPath = $refPath
                $candidatesReachingRefinement += 1
              }
              try {
                if (-not (Test-Path -LiteralPath $refPath)) { throw 'REFINEMENT_ARTIFACT_MISSING' }
                $rdoc = Get-Content -LiteralPath $refPath -Raw | ConvertFrom-Json
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
          if ($execCount -gt 0) {
            $backfillOutcomeQueue += [pscustomobject]@{ spec = [string]$spPath; batch = [string]$batchArtifactPath; refinement = [string]$backfillRefPath }
          }
        } catch {
          $bfErr = 'backfill_error'
          try { $bfErr = [string]$_.Exception.Message } catch {}
          Emit-Summary 'BATCH_BACKTEST_SUMMARY' ('Batch(backfill): runs=0 executed=0 skipped=0 (error) spec=' + [IO.Path]::GetFileName([string]$spPath) + ' detail=' + $bfErr) 'FAIL' 'Backtester'
          $batchEmitted = $true
        }
      }
    } catch {}
  }

  if (-not $batchEmitted -and -not $DryRun) {
    Emit-Summary 'BATCH_BACKTEST_SUMMARY' 'Batch: runs=0 executed=0 skipped=0 (skipped: no variants)' 'OK' 'Backtester'
    $batchEmitted = $true
  }

  if (-not $DryRun -and @($backfillOutcomeQueue).Count -gt 0) {
    foreach ($oq in @($backfillOutcomeQueue | Select-Object -First 3)) {
      $backfillRunId = ($CycleRunId + '-backfill-' + [IO.Path]::GetFileNameWithoutExtension([string]$oq.spec))
      $outcomePath = Invoke-OutcomeWorker $backfillRunId ([string]$oq.batch) ([string]$oq.refinement)
      if (-not [string]::IsNullOrWhiteSpace([string]$outcomePath)) {
        $generatedPath = Invoke-DirectiveDrivenSpecGeneration ([string]$oq.spec) ([string]$outcomePath)
        if (-not [string]::IsNullOrWhiteSpace([string]$generatedPath)) {
          $directiveBackfillSpecsGenerated += 1
        }
      }
    }
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

    if (($bundlesProcessed -gt 0) -and ($batchExecuted -gt 0 -or $refinementsRun -gt 0)) {
      $mainOutcomePath = Invoke-OutcomeWorker $CycleRunId $latestBatchArtifactPath $latestRefinementArtifactPath
      if (-not [string]::IsNullOrWhiteSpace([string]$mainOutcomePath) -and -not [string]::IsNullOrWhiteSpace([string]$latestStrategySpecPath)) {
        $generatedPathMain = Invoke-DirectiveDrivenSpecGeneration ([string]$latestStrategySpecPath) ([string]$mainOutcomePath)
        if (-not [string]::IsNullOrWhiteSpace([string]$generatedPathMain)) {
          $directiveBackfillSpecsGenerated += 1
        }
      }
    }
  }

}
catch {
  $errorsCount += 1
  if (-not $DryRun) {
    $errText = 'UNKNOWN_AUTOPILOT_ERROR'
    try { $errText = [string]$_.Exception.Message } catch {}
    Emit-Summary 'AUTOPILOT_EXCEPTION' ('Autopilot try-block exception: ' + $errText) 'FAIL' 'Autopilot'
  }
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
      $latestIsDirectiveContext = (-not [string]::IsNullOrWhiteSpace([string]$latestSpecObj.source_outcome_notes_path)) -or ([string]$latestSpecObj.generation_origin -like 'directive-generated*')
      $directiveVariantsEmitted = @($latestVariants | Where-Object {
        $origin = [string]$_.origin
        ($origin -eq 'DIRECTIVE') -or ($latestIsDirectiveContext -and $origin -eq 'DIVERSITY')
      }).Count
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
  directive_backfill_specs_generated = [int]$directiveBackfillSpecsGenerated
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
$labCounters = [ordered]@{ directive_loop_stall_cycles = 0; recent_backfill_specs = @(); updated_at = [DateTime]::UtcNow.ToString('o') }
if (Test-Path $labCountersPath) {
  try {
    $labPrev = Get-Content $labCountersPath -Raw | ConvertFrom-Json
    if ($null -ne $labPrev.directive_loop_stall_cycles) { $labCounters.directive_loop_stall_cycles = [int]$labPrev.directive_loop_stall_cycles }
    if ($null -ne $labPrev.recent_backfill_specs) { $labCounters.recent_backfill_specs = @($labPrev.recent_backfill_specs | ForEach-Object { [string]$_ }) }
  } catch {}
}
if (([int]$directiveNotesSeen -eq 0) -or ([int]$directiveVariantsEmitted -eq 0)) {
  $labCounters.directive_loop_stall_cycles = [int]$labCounters.directive_loop_stall_cycles + 1
} else {
  $labCounters.directive_loop_stall_cycles = 0
}
if (@($usedBackfillSpecs).Count -gt 0) {
  $combinedRecent = @($usedBackfillSpecs + @($labCounters.recent_backfill_specs))
  $labCounters.recent_backfill_specs = @($combinedRecent | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique | Select-Object -First 10)
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
  Emit-Summary 'LAB_SUMMARY' ("Lab: ingested=" + $candidatesIngested + " reached_refinement=" + $candidatesReachingRefinement + " passing_gate=" + $candidatesPassingGate + " directive_notes_seen=" + [int]$directiveNotesSeen + " directive_variants_emitted=" + [int]$directiveVariantsEmitted + " directive_backfill_specs_generated=" + [int]$directiveBackfillSpecsGenerated + " active_library_size=" + $activeLibrarySize + " bundles=" + $bundlesProcessed + " promotions=" + $promotionsProcessed + " refinements=" + $refinementsRun + " errors=" + $errorsCount) $aStatus 'oQ'
}

Write-Output ($summary | ConvertTo-Json -Depth 5)

# Explicit exit for scheduled task success reporting
exit 0


