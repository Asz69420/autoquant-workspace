param(
  [Parameter(Mandatory = $true)][string]$Message,
  [string]$UpdateId,
  [string]$MessageId,
  [string]$ChatId,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$IdemPath = 'data/state/ingress_idempotency.json'
$IdemTtlSec = 600
$IntentRegistryPath = 'config/intent_registry.json'
$ClarifierStatePath = 'data/state/clarifier_state.json'
$ClarifierTtlSec = 600
$UserMdPath = 'USER.md'

. "$PSScriptRoot/build_queue_lib.ps1"

function Get-IdempotencyKey {
  if (-not [string]::IsNullOrWhiteSpace($UpdateId)) { return ('tg:update:' + $UpdateId) }
  if (-not [string]::IsNullOrWhiteSpace($MessageId) -and -not [string]::IsNullOrWhiteSpace($ChatId)) { return ('tg:msg:' + $ChatId + ':' + $MessageId) }
  $bucket = [int]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() / 60)
  $chatPart = if ([string]::IsNullOrWhiteSpace($ChatId)) { '' } else { $ChatId }
  $raw = ($chatPart + '|' + $Message + '|' + $bucket)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
  $hash = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
  return ('fallback:' + $hash)
}

function Should-SkipByIdempotency {
  param([string]$Key)
  $dir = Split-Path -Parent $IdemPath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $cache = @{}
  if (Test-Path $IdemPath) {
    try {
      $raw = Get-Content $IdemPath -Raw
      if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $obj = ConvertFrom-Json $raw
        foreach ($p in $obj.PSObject.Properties) { $cache[$p.Name] = [int64]$p.Value }
      }
    } catch { $cache = @{} }
  }

  # GC expired
  $alive = @{}
  foreach ($k in $cache.Keys) {
    $ts = [int64]$cache[$k]
    if (($now - $ts) -lt $IdemTtlSec) { $alive[$k] = $ts }
  }

  $skip = $false
  if ($alive.ContainsKey($Key)) {
    $skip = $true
  } else {
    $alive[$Key] = $now
  }

  ($alive | ConvertTo-Json -Depth 4) | Set-Content -Path $IdemPath -Encoding utf8
  return $skip
}

function Emit-LogEvent {
  param(
    [string]$RunId,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary,
    [string[]]$Inputs,
    [string[]]$Outputs
  )
  $args = @('scripts/log_event.py','--run-id',$RunId,'--agent','oQ','--model-id','openai-codex/gpt-5.3-codex','--action','request_router','--status-word',$StatusWord,'--status-emoji',$StatusEmoji,'--summary',$Summary)
  if ($ReasonCode) { $args += @('--reason-code',$ReasonCode) }
  if ($Inputs) { foreach($i in $Inputs){ $args += @('--inputs',$i) } }
  if ($Outputs) { foreach($o in $Outputs){ $args += @('--outputs',$o) } }
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  python @args 2>$null | Out-Null
  $ErrorActionPreference = $oldEap
}

function Get-LatestReadyBuildId {
  if (-not (Test-Path 'build_session_ledger.jsonl')) { return '' }
  $latest = @{}
  Get-Content build_session_ledger.jsonl | ForEach-Object {
    if ([string]::IsNullOrWhiteSpace($_)) { return }
    $o = $_ | ConvertFrom-Json
    $latest[$o.build_session_id] = $o
  }
  $ready = @($latest.Values | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' } | Sort-Object last_update_at -Descending)
  if ($ready.Count -eq 0) { return '' }
  return [string]$ready[0].build_session_id
}

function Ensure-RuntimeFlags {
  $dir = 'config'
  $path = 'config/runtime_flags.json'
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  if (-not (Test-Path $path)) {
    Set-Content -Path $path -Value '{"warningsEnabled": true}' -Encoding utf8
  }
  return $path
}

function Ensure-IntentRegistry {
  if (-not (Test-Path $IntentRegistryPath)) {
    throw "Missing intent registry at $IntentRegistryPath"
  }
  return (Get-Content $IntentRegistryPath -Raw | ConvertFrom-Json)
}

function Match-WildcardPattern {
  param([string]$Text,[string]$Pattern)
  $rx = [Regex]::Escape($Pattern).Replace('\*','(.+)')
  $m = [Regex]::Match($Text, ('^' + $rx + '$'), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  if (-not $m.Success) { return $null }
  $captures = @()
  if ($m.Groups.Count -gt 1) {
    for ($i = 1; $i -lt $m.Groups.Count; $i++) {
      $captures += $m.Groups[$i].Value.Trim()
    }
  }
  return [PSCustomObject]@{ Captures = $captures }
}

function Resolve-Intent {
  param([object]$Registry,[string]$InputText)
  if ($null -eq $Registry -or $null -eq $Registry.intents) { return $null }
  foreach ($intent in $Registry.intents) {
    if ($null -eq $intent.patterns) { continue }
    foreach ($pattern in $intent.patterns) {
      $mm = Match-WildcardPattern -Text $InputText -Pattern ([string]$pattern)
      if ($null -ne $mm) {
        return [PSCustomObject]@{
          Intent = $intent
          Captures = $mm.Captures
        }
      }
    }
  }
  return $null
}

function Get-IdentityCanonical {
  $parsedAssistant = ''
  $parsedUser = ''
  $legacyAssistant = ''
  $legacyUser = ''
  $defaultAssistant = 'oQ'
  $defaultUser = 'Asz'

  if (Test-Path $UserMdPath) {
    try {
      $lines = Get-Content $UserMdPath
      foreach ($line in $lines) {
        if ($line -match '^\s*-\s*Assistant name\s*:\s*(.+?)\s*$') {
          if ([string]::IsNullOrWhiteSpace($parsedAssistant)) { $parsedAssistant = $matches[1].Trim() }
        }
        if ($line -match '^\s*-\s*User preferred name\s*:\s*(.+?)\s*$') {
          if ([string]::IsNullOrWhiteSpace($parsedUser)) { $parsedUser = $matches[1].Trim() }
        }
        if ($line -match '^\s*-\s*Name\s*:\s*(.+?)\s*$') {
          if ([string]::IsNullOrWhiteSpace($legacyAssistant)) { $legacyAssistant = $matches[1].Trim() }
        }
        if ($line -match '^\s*-\s*Preferred user name\s*:\s*(.+?)\s*$') {
          if ([string]::IsNullOrWhiteSpace($legacyUser)) { $legacyUser = $matches[1].Trim() }
        }
      }
    } catch {}
  }

  $hasParsed = (-not [string]::IsNullOrWhiteSpace($parsedAssistant) -and -not [string]::IsNullOrWhiteSpace($parsedUser))
  if (-not $hasParsed) {
    return [PSCustomObject]@{ Assistant = $defaultAssistant; User = $defaultUser }
  }

  $correctedAssistant = $parsedAssistant
  $correctedUser = $parsedUser

  $swapDetected = $false
  if ((-not [string]::IsNullOrWhiteSpace($legacyAssistant)) -and (-not [string]::IsNullOrWhiteSpace($legacyUser))) {
    $swapDetected = ($parsedAssistant -ieq $legacyUser -and $parsedUser -ieq $legacyAssistant)
    if ($swapDetected) {
      $correctedAssistant = $legacyAssistant
      $correctedUser = $legacyUser
    }
  }

  if ($correctedAssistant -ieq $correctedUser) {
    Emit-LogEvent -RunId ('identity-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'IDENTITY_SWAP_DETECTED' -Summary 'Identity equal; defaults applied' -Inputs @('parsed_assistant=' + $parsedAssistant,'parsed_user=' + $parsedUser) -Outputs @('corrected_assistant=' + $defaultAssistant,'corrected_user=' + $defaultUser)
    return [PSCustomObject]@{ Assistant = $defaultAssistant; User = $defaultUser }
  }

  if ($swapDetected) {
    Emit-LogEvent -RunId ('identity-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'IDENTITY_SWAP_DETECTED' -Summary 'Identity swapped; corrected using USER.md parsed values' -Inputs @('parsed_assistant=' + $parsedAssistant,'parsed_user=' + $parsedUser) -Outputs @('corrected_assistant=' + $correctedAssistant,'corrected_user=' + $correctedUser)
  }

  return [PSCustomObject]@{ Assistant = $correctedAssistant; User = $correctedUser }
}

function Get-ClarifierKey {
  if (-not [string]::IsNullOrWhiteSpace($ChatId)) { return ('chat:' + $ChatId) }
  if (-not [string]::IsNullOrWhiteSpace($MessageId)) { return ('msg:' + $MessageId) }
  return 'default'
}

function Get-ClarifierState {
  $dir = Split-Path -Parent $ClarifierStatePath
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  if (-not (Test-Path $ClarifierStatePath)) { return @{} }
  try {
    $raw = Get-Content $ClarifierStatePath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
    $obj = ConvertFrom-Json $raw
    $map = @{}
    foreach ($p in $obj.PSObject.Properties) { $map[$p.Name] = $p.Value }
    return $map
  } catch {
    return @{}
  }
}

function Save-ClarifierState {
  param([hashtable]$State)
  ($State | ConvertTo-Json -Depth 6) | Set-Content -Path $ClarifierStatePath -Encoding utf8
}

function Set-PendingClarifier {
  param([string]$Key,[string]$OriginalMessage)
  $state = Get-ClarifierState
  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $alive = @{}
  foreach ($k in $state.Keys) {
    $entry = $state[$k]
    $ts = [int64]$entry.ts
    if (($now - $ts) -lt $ClarifierTtlSec) { $alive[$k] = $entry }
  }
  $alive[$Key] = @{ ts = $now; original = $OriginalMessage }
  Save-ClarifierState -State $alive
}

function Pop-PendingClarifier {
  param([string]$Key)
  $state = Get-ClarifierState
  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $alive = @{}
  $val = $null
  foreach ($k in $state.Keys) {
    $entry = $state[$k]
    $ts = [int64]$entry.ts
    if (($now - $ts) -lt $ClarifierTtlSec) {
      if ($k -eq $Key) { $val = $entry } else { $alive[$k] = $entry }
    }
  }
  Save-ClarifierState -State $alive
  return $val
}

function Build-QuestionFromIntent {
  param([object]$Intent,[string[]]$Captures)
  $name = [string]$Intent.name
  if ($name -eq 'set_user_name') {
    $rawVal = if ($Captures.Count -ge 1) { $Captures[0] } else { '' }
    return ('Update USER.md: set User preferred name to "' + $rawVal + '". Keep all routing/verifier/keeper/logger/queue behavior unchanged.')
  }
  if ($name -eq 'set_assistant_name') {
    $rawVal = if ($Captures.Count -ge 1) { $Captures[0] } else { '' }
    return ('Update USER.md: set Assistant name to "' + $rawVal + '" in canonical identity. Keep all routing/verifier/keeper/logger/queue behavior unchanged.')
  }
  return $Message
}

# Deterministic routing rules (verbatim)
# FAST_PATH allowed actions (exact):
# - toggle a boolean setting / switch (enable/disable a feature flag)
# - read-only status queries (show pending builds, show latest status, show logs summary)
# - apply latest ready build / reject latest ready build
# - show help / usage
# - show debug/details (read artifacts/ledgers only)
# BUILD_PATH triggered when any are true:
# - user asks to build / implement / patch / update / add feature / refactor
# - request would modify code/files/config other than config/runtime_flags.json
# - request creates new files outside tests/docs
# Default on uncertainty: BUILD_PATH

$m = $Message.ToLowerInvariant().Trim()
$route = 'BUILD_PATH'
$rule = 'default_unsure_to_build'
$intentMatch = $null
$intentAction = ''
$intentName = ''
$buildQuestion = $Message

$idemKey = Get-IdempotencyKey
if (Should-SkipByIdempotency -Key $idemKey) {
  $skipRunId = 'route-skip-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  Emit-LogEvent -RunId $skipRunId -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'IDEMPOTENT_SKIP' -Summary 'Duplicate ingress message skipped' -Inputs @($idemKey) -Outputs @('SKIPPED')
  Write-Output 'Done — duplicate message ignored.'
  exit 0
}

$runId = 'route-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

# Clarifier response handling (single question flow)
$clarifierKey = Get-ClarifierKey
$pendingClarifier = Pop-PendingClarifier -Key $clarifierKey
if ($null -ne $pendingClarifier) {
  if ($m -match '^(change it|change|yes change|make changes)$') {
    $route = 'BUILD_PATH'
    $rule = 'clarifier_change_it'
    $buildQuestion = [string]$pendingClarifier.original
  } elseif ($m -match '^(just explain|explain|only explain)$') {
    $route = 'FAST_PATH'
    $rule = 'clarifier_just_explain'
    $intentAction = 'clarifier_explain'
  }
}

if ($rule -ne 'clarifier_change_it' -and $rule -ne 'clarifier_just_explain') {
  $registry = Ensure-IntentRegistry
  $intentMatch = Resolve-Intent -Registry $registry -InputText $m
  if ($null -ne $intentMatch) {
    $intentName = [string]$intentMatch.Intent.name
    $intentAction = [string]$intentMatch.Intent.action
    $route = [string]$intentMatch.Intent.route
    $rule = 'intent_registry_first_match'
    if ($route -eq 'BUILD_PATH') {
      $trimmed = $m.Trim()
      $singleWord = ($trimmed -notmatch '\s')
      $veryShort = ($trimmed.Length -lt 4)
      if ($veryShort -or $singleWord) {
        Set-PendingClarifier -Key $clarifierKey -OriginalMessage $Message
        Emit-LogEvent -RunId ($runId + '-intent-short') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'AMBIGUOUS_CLARIFIER' -Summary 'Short/ambiguous BUILD_PATH intent; asked clarifier' -Inputs @($Message) -Outputs @('clarifier_asked')
        Write-Output 'Do you want me to change something, or just explain?'
        Write-Output 'Options: Change it / Just explain'
        exit 0
      }
      $buildQuestion = Build-QuestionFromIntent -Intent $intentMatch.Intent -Captures $intentMatch.Captures
      [void](Get-IdentityCanonical)
    }
    Emit-LogEvent -RunId ($runId + '-intent') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'INTENT_MATCH' -Summary ('intent=' + $intentName + '; route=' + $route) -Inputs @($Message) -Outputs @($intentName,$route)
  }
}

if ($null -eq $intentMatch -and $rule -ne 'clarifier_change_it' -and $rule -ne 'clarifier_just_explain') {
  $buildVerbs = @('build','implement','patch','update','add feature','refactor')
  $fastStatus = @('show pending builds','any builds waiting for approval','builds waiting for approval','show latest status','show logs summary','show debug','details','help','usage','queue status','cancel next','clear queue','do i need to approve','what''s pending','whats pending','any builds waiting','mono test')
  $fastApply = @('apply latest','reject latest','apply','go ahead','yes apply','ok apply','ship it')
  $toggleWarnOff = @('turn warnings off','disable warnings','warnings off')
  $toggleWarnOn = @('turn warnings on','enable warnings','warnings on')

  if ($toggleWarnOff | Where-Object { $m.Contains($_) }) {
    $route = 'FAST_PATH'; $rule = 'toggle_boolean_setting'; $intentAction = 'toggle_warnings_off'
  } elseif ($toggleWarnOn | Where-Object { $m.Contains($_) }) {
    $route = 'FAST_PATH'; $rule = 'toggle_boolean_setting'; $intentAction = 'toggle_warnings_on'
  } elseif ($fastApply | Where-Object { $m.Contains($_) }) {
    $route = 'FAST_PATH'; $rule = 'apply_or_reject_latest_ready_build'; $intentAction = 'apply_latest'
  } elseif ($fastStatus | Where-Object { $m.Contains($_) }) {
    $route = 'FAST_PATH'; $rule = 'read_only_query_or_help'; $intentAction = 'status_or_help'
  } elseif ($buildVerbs | Where-Object { $m.Contains($_) }) {
    $route = 'BUILD_PATH'; $rule = 'explicit_build_intent'
  }

  if ($route -eq 'BUILD_PATH' -and $rule -eq 'default_unsure_to_build') {
    Set-PendingClarifier -Key $clarifierKey -OriginalMessage $Message
    Emit-LogEvent -RunId ($runId + '-clarifier') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'AMBIGUOUS_CLARIFIER' -Summary 'Asked single clarifier question' -Inputs @($Message) -Outputs @('clarifier_asked')
    Write-Output 'Do you want me to change something, or just explain?'
    Write-Output 'Options: Change it / Just explain'
    exit 0
  }
}

Emit-LogEvent -RunId $runId -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'ROUTE_DECISION' -Summary ("route=" + $route + "; rule=" + $rule) -Inputs @($Message) -Outputs @($route)

if ($route -eq 'FAST_PATH') {
  if ($intentAction -eq 'clarifier_explain') {
    Write-Output "Got it - I will explain only. Tell me what you want explained."
    exit 0
  }

  if ($intentAction -eq 'emit_insight_card') {
    $concept = ''
    if ($Message -match '^\s*(?:idea|insight|concept)\s+(.+)$') {
      $concept = $matches[1].Trim()
    }
    if ([string]::IsNullOrWhiteSpace($concept)) {
      Write-Output 'Share the insight after the keyword (idea/insight/concept).'
      exit 0
    }

    $words = @($concept -split '\s+' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $titleWords = @($words | Select-Object -First 6)
    $title = ($titleWords -join ' ').Trim()
    if ([string]::IsNullOrWhiteSpace($title)) { $title = 'Manual insight' }

    if ($DryRun) {
      Emit-LogEvent -RunId ($runId + '-insight-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would emit insight card' -Inputs @($concept) -Outputs @('would_run:scripts/pipeline/emit_insight_card.py')
      Write-Output 'Insight recorded.'
      exit 0
    }

    python scripts/pipeline/emit_insight_card.py --title $title --concept $concept | Out-Null
    Emit-LogEvent -RunId ($runId + '-insight') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'INSIGHT_RECORDED' -Summary 'Manual insight card emitted' -Inputs @($concept) -Outputs @('artifact=insight_card')
    Write-Output 'Insight recorded.'
    exit 0
  }

  if ($intentAction -eq 'show_roster' -or $m -eq 'roster' -or $m -eq 'show roster' -or $m -eq 'agent roster' -or $m -eq 'roster details') {
    Write-Output "✅ Active Agents (LLM)"
    Write-Output "🤖 oQ - Main orchestrator and delegation control."
    Write-Output "🔰 Verifier - Independent QC gate for policy and compatibility checks."
    Write-Output "🗃️ Keeper - Artifact indexing, dedup, and memory curation authority."
    Write-Output "🧾 Logger - Outbox drain + NDJSON action/error logging authority."
    Write-Output "🛡️ Firewall - Spec/security guard and write-allowlist enforcement."
    Write-Output "⏱️ Scheduler - Timing, cron orchestration, recurring task control."
    Write-Output "🔗 Reader - Source ingestion into ResearchCards."
    Write-Output "🧲 Grabber - TradingView indicator harvesting into IndicatorRecords."
    Write-Output "🕵️ Specter - Browser-AI bridge for schema-validated interactions (partial)."
    Write-Output "🧠 Analyser - Falsifiable thesis generation from research inputs."
    Write-Output "📊 Strategist - Thesis-to-StrategySpec translation."
    Write-Output "📈 Backtester - Batch backtest execution and report output."

    Write-Output "✅ Active Systems (Scripts)"
    Write-Output "🧵 Build Queue Worker - Single-flight queued BUILD_PATH execution."
    Write-Output "📣 TG Reporter - High-signal Telegram reporting and filters."
    Write-Output "🗄️ HL Data Ingest - Hyperliquid OHLCV ingestion + validation."
    Write-Output "🧪 HL Backtest Engine - Core hl_backtest_engine.py runner."
    Write-Output "📦 Batch Backtest Runner - Batch runs + experiment-plan emission."
    Write-Output "🔁 Refinement Loop Runner - run_refinement_loop.py bounded refinement loop."
    Write-Output "📚 Librarian v1 - run_librarian.py + dedup + archive management."
    Write-Output "🧾 Stage Verifiers - Stage1/2/3 verifiers + stage4 gates."
    Write-Output "📤 TV Exporter - WIP; blocked on reliable real-download capture."
    Write-Output "🧪 TV Parity Harness - WIP parity validation against TV trade outputs."

    Write-Output "🛠️ Planned"
    Write-Output "🏁 Ranker - Planned ranking across regimes and constraints."
    Write-Output "📚 Librarian (agent form) - Planned persona wrapper over active Librarian v1 system."
    Write-Output "🔁 Refiner (agent form) - Planned persona wrapper over active refinement loop system."
    Write-Output "🧑‍💻 Coder - Planned Pine/Python conversion and adapter maintainer."
    Write-Output "⚡ Executor-HL - Planned live Hyperliquid executor under guardrails."
    Write-Output "🛑 Risk Manager - Planned live risk and circuit-breaker enforcement."
    exit 0
  }

  if ($intentAction -eq 'make_review_pack' -or $m -eq 'make review pack' -or $m -eq 'review pack' -or $m -eq 'prep opus review') {
    $scope = ''
    if ($null -ne $intentMatch -and $intentMatch.Captures -and $intentMatch.Captures.Count -gt 0) { $scope = [string]$intentMatch.Captures[0] }
    if ([string]::IsNullOrWhiteSpace($scope)) {
      Write-Output 'What should the review be about?'
      exit 0
    }
    $latestCommit = (git rev-parse --short HEAD)
    $auto = 'data/state/autopilot_summary.json'
    $top = 'artifacts/library/TOP_CANDIDATES.json'
    $less = 'artifacts/library/LESSONS_INDEX.json'
    $title = 'Opus review - ' + $scope
    $pack = python scripts/pipeline/make_review_pack.py --title $title --scope $scope --commit $latestCommit --artifacts ($auto + ',' + $top + ',' + $less)
    $packObj = $pack | ConvertFrom-Json
    Write-Output ('Review pack ready: ' + [string]$packObj.review_pack_path)
    exit 0
  }

  if ($m -eq 'mono test') {
    $mono = @(
      'AAA   BBB'
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      '111   222'
    ) -join "`n"
    Emit-LogEvent -RunId ($runId + '-mono-test') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'MONO_TEST' -Summary 'Rendered monospace probe text' -Inputs @($Message) -Outputs @('mono_probe')
    Write-Output $mono
    exit 0
  }

  if ($intentAction -eq 'show_leaderboard' -or $m -like 'leaderboard*') {
    $writerOut = (python scripts/pipeline/write_leaderboard_txt.py --send-telegram) -join "`n"
    $writerObj = $null
    try { $writerObj = $writerOut | ConvertFrom-Json } catch { $writerObj = $null }

    if ($null -eq $writerObj -or -not $writerObj.ok) {
      Emit-LogEvent -RunId ($runId + '-leaderboard-fail') -StatusWord 'FAIL' -StatusEmoji '❌' -ReasonCode 'LEADERBOARD_PLACEHOLDER_DETECTED' -Summary 'leaderboard.txt generation failed; blocked send' -Inputs @($Message) -Outputs @('blocked')
      Write-Output 'leaderboard.txt'
      exit 2
    }

    Emit-LogEvent -RunId ($runId + '-leaderboard') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'LEADERBOARD' -Summary 'Generated and sent leaderboard.txt' -Inputs @($Message) -Outputs @(('assets=' + [string]$writerObj.assets_included),('rows=' + [string]$writerObj.rows_included),('placeholders=' + [string]$writerObj.placeholders_found))
    Write-Output 'leaderboard.txt'
    exit 0
  }

  if ($intentAction -eq 'show_report' -or $m -eq 'report' -or $m -eq 'status report' -or $m -eq 'lab report' -or $m -eq 'top candidates') {
    $topPath = 'artifacts/library/TOP_CANDIDATES.json'
    $lessonPath = 'artifacts/library/LESSONS_INDEX.json'
    $autoPath = 'data/state/autopilot_summary.json'

    $top = @()
    if (Test-Path $topPath) {
      try { $top = @(Get-Content $topPath -Raw | ConvertFrom-Json) } catch { $top = @() }
    }
    $lessons = @()
    if (Test-Path $lessonPath) {
      try { $lessons = @(Get-Content $lessonPath -Raw | ConvertFrom-Json) } catch { $lessons = @() }
    }
    $auto = $null
    if (Test-Path $autoPath) {
      try { $auto = Get-Content $autoPath -Raw | ConvertFrom-Json } catch { $auto = $null }
    }

    Write-Output 'Lab Report'
    Write-Output 'Top candidates:'
    $top5 = @($top | Select-Object -First 5)
    if ($top5.Count -eq 0) {
      Write-Output '- none yet'
    } else {
      foreach ($c in $top5) {
        $ds = if ($c.datasets_tested -and $c.datasets_tested.Count -gt 0) { ($c.datasets_tested[0].symbol + '/' + $c.datasets_tested[0].timeframe) } else { 'n/a' }
        $pf = if ($c.profit_factor -is [System.Array]) { $c.profit_factor[0] } else { $c.profit_factor }
        $dd = if ($c.max_drawdown -is [System.Array]) { $c.max_drawdown[0] } else { $c.max_drawdown }
        $tr = if ($c.trades -is [System.Array]) { $c.trades[0] } else { $c.trades }
        $np = if ($c.net_profit -is [System.Array]) { $c.net_profit[0] } else { $c.net_profit }
        Write-Output ("- " + $ds + " | PF " + [string]$pf + " | DD " + [string]$dd + " | trades " + [string]$tr + " | net " + [string]$np)
      }
    }

    Write-Output 'Latest lessons:'
    $l2 = @($lessons | Select-Object -First 2)
    if ($l2.Count -eq 0) {
      Write-Output '- none'
    } else {
      foreach ($l in $l2) {
        $pat = if ($l.pattern -is [System.Array]) { $l.pattern[0] } else { $l.pattern }
        $sug = if ($l.suggestion -is [System.Array]) { $l.suggestion[0] } else { $l.suggestion }
        Write-Output ("- " + [string]$pat + ": " + [string]$sug)
      }
    }

    if ($null -ne $auto) {
      Write-Output ("Autopilot: bundles " + [string]$auto.bundles_processed + ", promotions " + [string]$auto.promotions_processed + ", refinements " + [string]$auto.refinements_run + ", new indicators " + [string]$auto.new_indicators_added + ", dedup skips " + [string]$auto.skipped_indicators_dedup + ", new candidates " + [string]$auto.new_candidates_count + ", errors " + [string]$auto.errors_count)
    } else {
      Write-Output 'Autopilot: no recent summary'
    }
    exit 0
  }

  if ($intentAction -eq 'toggle_warnings_off' -or $m.Contains('turn warnings off') -or $m.Contains('disable warnings') -or $m.Contains('warnings off')) {
    $f = 'config/runtime_flags.json'
    if ($DryRun) {
      Emit-LogEvent -RunId ($runId + '-toggle-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would set warningsEnabled=false' -Inputs @($f) -Outputs @('would_set:warningsEnabled=false')
      Write-Output 'Dry run — would set warningsEnabled=false.'
      exit 0
    }
    $f = Ensure-RuntimeFlags
    $obj = Get-Content $f -Raw | ConvertFrom-Json
    $obj.warningsEnabled = $false
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $f -Encoding utf8
    Emit-LogEvent -RunId ($runId + '-toggle') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'SETTING_TOGGLED' -Summary 'warningsEnabled=false' -Inputs @($f) -Outputs @('warningsEnabled=false')
    Write-Output 'Done — warnings are now off.'
    exit 0
  }

  if ($intentAction -eq 'toggle_warnings_on' -or $m.Contains('turn warnings on') -or $m.Contains('enable warnings') -or $m.Contains('warnings on')) {
    $f = 'config/runtime_flags.json'
    if ($DryRun) {
      Emit-LogEvent -RunId ($runId + '-toggle-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would set warningsEnabled=true' -Inputs @($f) -Outputs @('would_set:warningsEnabled=true')
      Write-Output 'Dry run — would set warningsEnabled=true.'
      exit 0
    }
    $f = Ensure-RuntimeFlags
    $obj = Get-Content $f -Raw | ConvertFrom-Json
    $obj.warningsEnabled = $true
    $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $f -Encoding utf8
    Emit-LogEvent -RunId ($runId + '-toggle') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'SETTING_TOGGLED' -Summary 'warningsEnabled=true' -Inputs @($f) -Outputs @('warningsEnabled=true')
    Write-Output 'Done — warnings are now on.'
    exit 0
  }

  if ($intentAction -eq 'apply_latest_ready' -or $intentAction -eq 'apply_latest' -or $m -eq 'apply latest' -or $m -eq 'apply' -or $m -eq 'go ahead' -or $m -eq 'yes apply' -or $m -eq 'ok apply' -or $m -eq 'ship it') {
    $sid = Get-LatestReadyBuildId
    if ([string]::IsNullOrWhiteSpace($sid)) { Write-Output 'Done — there is no ready build to apply.'; exit 0 }
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would apply the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action APPROVE -BuildSessionId $sid | Out-Null
      Write-Output 'Done — applied the latest ready build.'
    }
    exit 0
  }

  if ($intentAction -eq 'reject_latest' -or $m.Contains('reject latest')) {
    $sid = Get-LatestReadyBuildId
    if ([string]::IsNullOrWhiteSpace($sid)) { Write-Output 'Done — there is no ready build to reject.'; exit 0 }
    if ($DryRun) {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid -DryRun | Out-Null
      Write-Output 'Dry run — would reject the latest ready build.'
    } else {
      powershell -ExecutionPolicy Bypass -File scripts/automation/approve_build_session.ps1 -Action REJECT -BuildSessionId $sid | Out-Null
      Write-Output 'Done — rejected the latest ready build.'
    }
    exit 0
  }

  if ($intentAction -eq 'show_pending_approvals' -or $m.Contains('show pending builds') -or $m.Contains('builds waiting for approval') -or $m.Contains('any builds waiting') -or $m.Contains('do i need to approve') -or $m.Contains('what''s pending') -or $m.Contains('whats pending')) {
    $arr = python scripts/automation/build_session.py show --limit 10 | ConvertFrom-Json
    $ready = @($arr | Where-Object { $_.state -eq 'SESSION_READY_FOR_APPROVAL' })
    if ($ready.Count -eq 0) { Write-Output 'No builds waiting for approval.'; exit 0 }
    Write-Output ("Pending approvals: " + $ready.Count)
    Write-Output ('Latest: ' + [string]$ready[0].description)
    exit 0
  }

  if ($m.Contains('show latest status')) {
    $one = python scripts/automation/build_session.py show --limit 1 | ConvertFrom-Json
    if ($one.Count -eq 0) { Write-Output 'No build session yet.'; exit 0 }
    Write-Output ('Latest build status: ' + [string]$one[0].state)
    exit 0
  }

  if ($m.Contains('show logs summary')) {
    Write-Output 'Recent activity is available in the logger channel.'
    exit 0
  }

  if ($m.Contains('queue status')) {
    $qs = Get-QueueStatus
    $active = $qs.Active
    $queue = @($qs.Queue)
    if ($null -eq $active) {
      if ($queue.Count -eq 0) {
        Write-Output 'Queue is empty. No active build.'
      } else {
        Write-Output ("No active build. Queued: " + $queue.Count)
        $top = @($queue | Select-Object -First 3)
        foreach ($j in $top) { Write-Output ("- " + [string]$j.question) }
      }
    } else {
      $activeExec = if ($active.executor_type) { [string]$active.executor_type } else { 'UNKNOWN' }
      Write-Output ("Active: " + [string]$active.question + " [executor_type=" + $activeExec + "]")
      Write-Output ("Queued: " + $queue.Count)
      $top = @($queue | Select-Object -First 3)
      foreach ($j in $top) { Write-Output ("- next: " + [string]$j.question) }
    }
    Emit-LogEvent -RunId ($runId + '-queue-status') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_STATUS' -Summary 'Queue status requested' -Inputs @($Message) -Outputs @(("active=" + [string]($null -ne $active)),("queued=" + $queue.Count))
    exit 0
  }

  if ($m.Contains('cancel next')) {
    $res = Cancel-NextJob
    if ($res.Cancelled) {
      Write-Output ("Cancelled first queued build: " + [string]$res.Job.question)
      Emit-LogEvent -RunId ($runId + '-cancel-next') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_CANCEL_NEXT' -Summary 'Cancelled first queued build' -Inputs @($Message) -Outputs @([string]$res.Job.job_id)
    } else {
      Write-Output 'No queued build to cancel.'
    }
    exit 0
  }

  if ($m.Contains('clear queue')) {
    $res = Clear-Queue
    Write-Output ("Cleared queued builds: " + $res.Cleared)
    Emit-LogEvent -RunId ($runId + '-clear-queue') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'QUEUE_CLEARED' -Summary ('Cleared queued builds: ' + $res.Cleared) -Inputs @($Message) -Outputs @([string]$res.Cleared)
    exit 0
  }

  if ($m.Contains('show debug') -or $m.Contains('details')) {
    python scripts/automation/build_session.py show --limit 5
    Get-Content task_ledger.jsonl -Tail 10
    exit 0
  }

  Write-Output 'Done — say what you want changed and I will route it automatically.'
  exit 0
}

# BUILD_PATH
if ($DryRun) {
  Emit-LogEvent -RunId ($runId + '-build-dryrun') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'DRYRUN_SKIPPED_WRITE' -Summary 'Dry run - would execute BUILD_PATH and start verification loop' -Inputs @($buildQuestion) -Outputs @('would_run:scripts/automation/run_work.ps1')
  Write-Output 'Dry run - would route to BUILD_PATH and start verification, then request approval.'
  exit 0
}
if ([string]::IsNullOrWhiteSpace($ChatId) -and [string]::IsNullOrWhiteSpace($MessageId) -and [string]::IsNullOrWhiteSpace($UpdateId)) {
  Emit-LogEvent -RunId ($runId + '-missing-target') -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'QUEUE_MISSING_CHAT_TARGET' -Summary 'Ingress metadata missing; enqueue will be log-only' -Inputs @($buildQuestion) -Outputs @('log_only_enqueue')
}
$enqueue = Enqueue-BuildJob -Question $buildQuestion -ChatId $ChatId -MessageId $MessageId -UpdateId $UpdateId -IdemKey $idemKey -ExecutorType 'LOCAL_SCRIPT'
if ($enqueue.ExecutorError) {
  Emit-LogEvent -RunId ($runId + '-executor') -StatusWord 'FAIL' -StatusEmoji '❌' -ReasonCode 'EXECUTOR_NOT_CONFIGURED' -Summary 'Build blocked: explicit executor not configured' -Inputs @($buildQuestion) -Outputs @('executor=none')
  Write-Output 'FAIL reason_code=EXECUTOR_NOT_CONFIGURED'
  exit 12
}
if ($enqueue.QueueFull) {
  Emit-LogEvent -RunId ($runId + '-queue-full') -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'QUEUE_FULL' -Summary ('Build queue full (cap=' + $enqueue.Cap + ')') -Inputs @($buildQuestion) -Outputs @('queue_full')
  Write-Output 'Queue is full right now. Please try again after current builds finish.'
  exit 9
}
if ($enqueue.Duplicate) {
  Write-Output 'Already queued. I will process it after the current build finishes.'
  exit 0
}
$jobId = [string]$enqueue.Job.job_id
$pos = [int]$enqueue.Position
Emit-LogEvent -RunId ($runId + '-enqueued') -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'BUILD_ENQUEUED' -Summary ('Build enqueued: ' + $jobId + ' position=' + $pos) -Inputs @($buildQuestion) -Outputs @($jobId,('position=' + $pos))
Write-Output ("Queued. Position: " + $pos + ". I will start it after the current build finishes.")
