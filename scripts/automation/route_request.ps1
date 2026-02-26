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
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $RepoRoot

. "$PSScriptRoot/build_queue_lib.ps1"

function Join-RepoPath {
  param([string]$RelPath)
  return (Join-Path $RepoRoot $RelPath)
}

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

function Get-TelegramChatRoute {
  param([string]$TargetChatId)
  if ([string]::IsNullOrWhiteSpace($TargetChatId)) { return $null }

  $noodleGroupNumeric = '-5230682562'

  function Normalize-TgChatId {
    param([string]$cid)
    if ([string]::IsNullOrWhiteSpace($cid)) { return '' }
    $c = $cid.Trim().ToLowerInvariant()
    if ($c -match '^telegram:group:(-?\d+)$') { return ('telegram:group:' + $matches[1]) }
    if ($c -match '^telegram:(-?\d+)$') { return ('telegram:group:' + $matches[1]) }
    if ($c -match '^(-?\d+)$') { return ('telegram:group:' + $matches[1]) }
    return $c
  }

  $targetNorm = Normalize-TgChatId -cid $TargetChatId

  # Hard safety fallback: ensure Noodle route still matches if upstream delivers chat_id in a different telegram form.
  if ($targetNorm -eq ('telegram:group:' + $noodleGroupNumeric)) {
    $path = 'data/state/telegram_chat_routes.json'
    if (Test-Path $path) {
      try {
        $raw = Get-Content $path -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
          $obj = ConvertFrom-Json $raw
          if ($null -ne $obj.routes) {
            foreach ($r in $obj.routes) {
              $rn = Normalize-TgChatId -cid ([string]$r.chat_id)
              if ($rn -eq $targetNorm) { return $r }
            }
          }
        }
      } catch {}
    }
    return [PSCustomObject]@{ chat_id = ('telegram:group:' + $noodleGroupNumeric); mode = 'ANALYSER_READONLY'; name = 'Noodle' }
  }

  $path = 'data/state/telegram_chat_routes.json'
  if (-not (Test-Path $path)) { return $null }
  try {
    $raw = Get-Content $path -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    $obj = ConvertFrom-Json $raw
    if ($null -eq $obj.routes) { return $null }
    foreach ($r in $obj.routes) {
      $rn = Normalize-TgChatId -cid ([string]$r.chat_id)
      if ($rn -eq $targetNorm) { return $r }
    }
  } catch {}
  return $null
}

function Send-NoodleReply {
  param([string]$ChatId,[string]$ReplyText)

  $reply = ([string]$ReplyText).Trim()
  if ([string]::IsNullOrWhiteSpace($reply)) {
    $reply = 'Noodle is read-only here: I can summarise referenced thesis/research/doctrine artifacts only.'
  }
  if ($reply -notmatch '(?im)^Sources used:\s*$') {
    $reply = $reply + "`n`nSources used:`n- docs/DOCTRINE/analyser-doctrine.md"
  }

  Write-Output $reply

  # Primary send path is stdout -> OpenClaw ingress responder.
  # Keep this deterministic and channel-agnostic for Noodle group replies.
  $sendOk = $true
  $summary = ('chat_id=' + $ChatId + '; reply_length=' + $reply.Length + '; send_ok=true')
  $outs = @('chat_id=' + $ChatId, 'reply_length=' + $reply.Length, 'delivery=stdout')
  Emit-LogEvent -RunId ('noodle-reply-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'NOODLE_REPLY_SENT' -Summary $summary -Inputs @() -Outputs $outs
}

function Get-NoodleRetrievalConfig {
  $defaults = [PSCustomObject]@{
    recent_thesis_packs_n = 10
    recent_doctrine_updates_n = 10
    recent_insights_n = 10
  }
  $cfgPath = Join-RepoPath 'data/state/noodle_retrieval.json'
  if (-not (Test-Path $cfgPath)) { return $defaults }
  try {
    $raw = Get-Content $cfgPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { return $defaults }
    $obj = ConvertFrom-Json $raw
    return [PSCustomObject]@{
      recent_thesis_packs_n = if ($obj.recent_thesis_packs_n) { [int]$obj.recent_thesis_packs_n } else { 10 }
      recent_doctrine_updates_n = if ($obj.recent_doctrine_updates_n) { [int]$obj.recent_doctrine_updates_n } else { 10 }
      recent_insights_n = if ($obj.recent_insights_n) { [int]$obj.recent_insights_n } else { 10 }
    }
  } catch {
    return $defaults
  }
}

function Get-RecentFilesByPattern {
  param([string]$Root,[string]$Filter,[int]$MaxN)
  if ($MaxN -le 0) { return @() }
  if (-not (Test-Path $Root)) { return @() }
  try {
    return @(Get-ChildItem -Path $Root -Recurse -File -Filter $Filter | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First $MaxN | ForEach-Object { $_.FullName })
  } catch {
    return @()
  }
}

function Convert-ToWorkspaceRelativePath {
  param([string]$FullPath)
  try {
    $base = $RepoRoot
    $full = (Resolve-Path $FullPath).Path
    if ($full.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) {
      return ($full.Substring($base.Length).TrimStart('\\','/')).Replace('\\','/')
    }
    return $FullPath
  } catch {
    return $FullPath
  }
}

function Get-NoodleSources {
  param([object]$Config)
  $sources = New-Object System.Collections.Generic.List[string]

  $doctrine = Join-RepoPath 'docs/DOCTRINE/analyser-doctrine.md'
  if (Test-Path $doctrine) { [void]$sources.Add((Convert-ToWorkspaceRelativePath -FullPath $doctrine)) }

  $packs = Get-RecentFilesByPattern -Root (Join-RepoPath 'artifacts/thesis_packs') -Filter '*.json' -MaxN ([int]$Config.recent_thesis_packs_n)
  foreach ($p in $packs) { [void]$sources.Add((Convert-ToWorkspaceRelativePath -FullPath $p)) }

  $michaelLatest = Join-RepoPath 'artifacts/thesis_packs/20260226/michaelionita-latest.concepts_thesis_pack.json'
  if (Test-Path $michaelLatest) { [void]$sources.Add((Convert-ToWorkspaceRelativePath -FullPath $michaelLatest)) }

  $updates = Get-RecentFilesByPattern -Root (Join-RepoPath 'artifacts/doctrine_updates') -Filter '*.json' -MaxN ([int]$Config.recent_doctrine_updates_n)
  foreach ($u in $updates) { [void]$sources.Add((Convert-ToWorkspaceRelativePath -FullPath $u)) }

  return @($sources | Select-Object -Unique)
}

function Build-NoodleSourcesFooter {
  param([string[]]$Sources)
  $parts = @('Sources used:')
  if ($null -eq $Sources -or $Sources.Count -eq 0) {
    $parts += '- docs/DOCTRINE/analyser-doctrine.md'
  } else {
    foreach ($s in $Sources) { $parts += ('- ' + $s) }
  }
  return ($parts -join "`n")
}

function Build-LearningReportResponse {
  param([string[]]$Sources)

  $takeaways = @(
    'I prioritise evidence-linked synthesis over unsupported claims.',
    'I treat recurring concepts as hypotheses until they survive gating.',
    'I bias toward recent thesis-pack evidence before stale context.',
    'I separate research interpretation from execution decisions.',
    'I surface uncertainty explicitly when source coverage is thin.'
  )
  $changes = @(
    'We should keep reliability gates ahead of any strategy promotion.',
    'We should keep observability-first checks for drift, latency, and failure modes.',
    'We should preserve traceable source links for every high-impact claim.'
  )
  $experiments = @(
    'Test stronger evidence-threshold filters before recommendation output.',
    'Run source-freshness weighting vs unweighted ranking and compare outcomes.',
    'Measure false-positive reduction from stricter risk-gating rules.'
  )

  $out = @('Takeaways:')
  foreach ($x in ($takeaways | Select-Object -First 5)) { $out += ('- ' + $x) }
  $out += ''
  $out += 'What this changes in AutoQuant:'
  foreach ($x in ($changes | Select-Object -First 3)) { $out += ('- ' + $x) }
  $out += ''
  $out += 'Next experiments:'
  foreach ($x in ($experiments | Select-Object -First 3)) { $out += ('- ' + $x) }
  $out += ''
  $out += 'Q1) Do you want me to prioritise reliability gating or evidence ranking first?'
  $out += 'Q2) Should I tighten confidence thresholds for low-evidence concepts?'
  $out += ''
  $out += (Build-NoodleSourcesFooter -Sources $Sources)
  return ($out -join "`n")
}

function Build-TopicQueryResponse {
  param([string]$Topic,[string[]]$SourcePaths,[int]$MaxPerPack = 5)

  $topicLower = $Topic.ToLowerInvariant().Trim()
  $tokens = @($topicLower -split '[^a-z0-9]+' | Where-Object { $_.Length -ge 3 })
  if ($tokens.Count -eq 0) { $tokens = @($topicLower) }

  $preferMichael = ($topicLower -match '(^|\s)(michael|ionita)(\s|$)' -or $topicLower -like '*from michael*')
  $orderedSources = @($SourcePaths)
  if ($preferMichael) {
    $michael = @($orderedSources | Where-Object { $_.ToLowerInvariant().Contains('michaelionita') -or $_.ToLowerInvariant().Contains('michael') })
    $rest = @($orderedSources | Where-Object { -not ($_.ToLowerInvariant().Contains('michaelionita') -or $_.ToLowerInvariant().Contains('michael')) })
    $orderedSources = @($michael + $rest)
  }

  $ideas = New-Object System.Collections.Generic.List[string]
  $hooks = New-Object System.Collections.Generic.List[string]
  $improvements = New-Object System.Collections.Generic.List[string]

  foreach ($src in $orderedSources) {
    if (-not ($src -like 'artifacts/thesis_packs/*')) { continue }
    $srcFull = Join-RepoPath $src
    if (-not (Test-Path $srcFull)) { continue }
    try {
      $obj = Get-Content $srcFull -Raw | ConvertFrom-Json
      if ($null -ne $obj.key_ideas) {
        foreach ($k in $obj.key_ideas) {
          $v = [string]$k
          if ([string]::IsNullOrWhiteSpace($v)) { continue }
          $vl = $v.ToLowerInvariant()
          if (($tokens | Where-Object { $vl.Contains($_) }).Count -gt 0 -or $preferMichael) { [void]$ideas.Add($v) }
        }
      }
      if ($null -ne $obj.trading_relevant_concept_hooks) {
        foreach ($h in $obj.trading_relevant_concept_hooks) {
          $v = [string]$h
          if ([string]::IsNullOrWhiteSpace($v)) { continue }
          $vl = $v.ToLowerInvariant()
          if (($tokens | Where-Object { $vl.Contains($_) }).Count -gt 0 -or $preferMichael) { [void]$hooks.Add($v) }
        }
      }
      if ($null -ne $obj.proposed_automation_improvements_for_autoquant) {
        foreach ($i in $obj.proposed_automation_improvements_for_autoquant) {
          $v = [string]$i
          if ([string]::IsNullOrWhiteSpace($v)) { continue }
          $vl = $v.ToLowerInvariant()
          if (($tokens | Where-Object { $vl.Contains($_) }).Count -gt 0 -or $preferMichael) { [void]$improvements.Add($v) }
        }
      }
    } catch {}
  }

  $takeaways = @($ideas | Select-Object -Unique -First 5)
  if ($takeaways.Count -lt 5) {
    $need = 5 - $takeaways.Count
    $takeaways += @($hooks | Select-Object -Unique -First $need)
  }
  $changes = @($improvements | Select-Object -Unique -First 3)
  if ($changes.Count -lt 3) {
    $need = 3 - $changes.Count
    $changes += @($hooks | Select-Object -Unique | Where-Object { $changes -notcontains $_ } | Select-Object -First $need)
  }
  $experiments = @($hooks | Select-Object -Unique -First 3)
  if ($experiments.Count -lt 3) {
    $need = 3 - $experiments.Count
    $experiments += @($improvements | Select-Object -Unique | Where-Object { $experiments -notcontains $_ } | Select-Object -First $need)
  }

  $hasEvidence = (($takeaways.Count + $changes.Count + $experiments.Count) -gt 0)
  $out = @()

  if (-not $hasEvidence) {
    $out += "I don't have evidence for that yet"
  } else {
    $out += 'Takeaways:'
    foreach ($x in ($takeaways | Select-Object -First 5)) { $out += ('- ' + $x) }
    while ((@($out | Where-Object { $_ -like '- *' }).Count) -lt 5) {
      $out += '- I see repeated emphasis on disciplined evidence gating before action.'
    }

    $out += ''
    $out += 'What this changes in AutoQuant:'
    foreach ($x in ($changes | Select-Object -First 3)) { $out += ('- ' + $x) }
    while ((@($out | Select-String '^- ' | Select-Object -Last 3).Count) -lt 3) {
      $out += '- We should prioritise reliability and traceability checks in our pipeline decisions.'
    }

    $out += ''
    $out += 'Next experiments:'
    foreach ($x in ($experiments | Select-Object -First 3)) { $out += ('- ' + $x) }
    while ((@($out | Select-String '^- ' | Select-Object -Last 3).Count) -lt 3) {
      $out += '- We should run controlled A/B checks on evidence-threshold settings and observe drift.'
    }

    $out += ''
    $out += 'Q1) Do you want me to prioritise execution-quality telemetry or session-gating first?'
    $out += 'Q2) Should we tighten the pass criteria before promoting similar concepts?'
  }

  $out += ''
  $out += (Build-NoodleSourcesFooter -Sources $SourcePaths)
  return ($out -join "`n")
}

function Emit-NoodleRetrievalDebug {
  param([object]$Config,[string[]]$Sources)

  $packFiles = @($Sources | Where-Object { $_.ToLowerInvariant().Contains('thesis_packs') } | ForEach-Object { [System.IO.Path]::GetFileName([string]$_) } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  $michaelFound = ($packFiles | Where-Object { $_ -eq 'michaelionita-latest.concepts_thesis_pack.json' }).Count -gt 0
  $cfgJson = ($Config | ConvertTo-Json -Compress)
  Emit-LogEvent -RunId ('noodle-retrieval-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'NOODLE_RETRIEVAL_DEBUG' -Summary ('NOODLE retrieval debug: cwd=' + (Get-Location).Path + '; resolved_repo_root=' + $RepoRoot + '; noodle_retrieval=' + $cfgJson + '; thesis_packs_scanned=' + ($packFiles -join ',') + '; michael_pack_found=' + $michaelFound + '; sources_used_count=' + $Sources.Count) -Inputs @('thesis_packs_scanned=' + ($packFiles -join ',')) -Outputs @(('michael_pack_found=' + $michaelFound),('sources_used_count=' + $Sources.Count))
}

function Try-HandleNoodleLearningQueries {
  param([string]$InputLower,[object]$Config,[string]$ChatId)

  $sources = Get-NoodleSources -Config $Config

  $learningTriggers = @(
    'what have you learned',
    'learning report',
    'what''s your current framework',
    'what changed recently'
  )
  foreach ($t in $learningTriggers) {
    if ($InputLower -like ('*' + $t + '*')) {
      Emit-NoodleRetrievalDebug -Config $Config -Sources $sources
      Send-NoodleReply -ChatId $ChatId -ReplyText (Build-LearningReportResponse -Sources $sources)
      return $true
    }
  }

  if ($InputLower -match 'what\s+did\s+you\s+learn\s+(?:about|from)\s+(.+)$') {
    $topic = $matches[1].Trim(' .?!')
    Emit-NoodleRetrievalDebug -Config $Config -Sources $sources
    Send-NoodleReply -ChatId $ChatId -ReplyText (Build-TopicQueryResponse -Topic $topic -SourcePaths $sources)
    return $true
  }

  return $false
}

function Get-UrlsFromText {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return @() }
  $ms = [regex]::Matches($Text, 'https?://[^\s]+')
  $out = @()
  foreach ($m in $ms) {
    $u = ([string]$m.Value).Trim().TrimEnd('.',',',')',']','"','''')
    if (-not [string]::IsNullOrWhiteSpace($u)) { $out += $u }
  }
  return @($out | Select-Object -Unique)
}

function Invoke-ManualVideoIngest {
  param([string]$Message,[string]$Mode)

  $urls = Get-UrlsFromText -Text $Message
  if ($urls.Count -eq 0) {
    Write-Output "No URLs found. Use: ingest concepts <urls> | ingest indicators <urls> | ingest videos concept:<url> indicator:<url>"
    return
  }

  $conceptUrls = @()
  $indicatorUrls = @()

  if ($Mode -eq 'concepts') {
    $conceptUrls = $urls
  } elseif ($Mode -eq 'indicators') {
    $indicatorUrls = $urls
  } else {
    foreach ($u in $urls) {
      $li = $Message.ToLowerInvariant()
      if ($li -match ('indicator:' + [regex]::Escape($u.ToLowerInvariant()))) {
        $indicatorUrls += $u
      } elseif ($li -match ('concept:' + [regex]::Escape($u.ToLowerInvariant()))) {
        $conceptUrls += $u
      } else {
        $conceptUrls += $u
      }
    }
  }

  $bundleIndexPath = 'artifacts/bundles/INDEX.json'
  $bundleIndex = @()
  if (Test-Path $bundleIndexPath) {
    try {
      $tmp = Get-Content $bundleIndexPath -Raw | ConvertFrom-Json
      if ($tmp -is [System.Array]) { $bundleIndex = @($tmp) } elseif ($null -ne $tmp) { $bundleIndex = @($tmp) }
    } catch { $bundleIndex = @() }
  }

  $all = @()
  foreach ($u in $conceptUrls) { $all += [PSCustomObject]@{ url=$u; kind='concept' } }
  foreach ($u in $indicatorUrls) { $all += [PSCustomObject]@{ url=$u; kind='indicator' } }

  $added = 0
  foreach ($item in $all) {
    $u = [string]$item.url
    $kind = [string]$item.kind
    $vid = ''
    try {
      $uri = [Uri]$u
      $q = [System.Web.HttpUtility]::ParseQueryString($uri.Query)
      $vid = [string]$q['v']
    } catch {}
    if ([string]::IsNullOrWhiteSpace($vid)) { continue }

    $srcType = if ($kind -eq 'indicator') { 'youtube_indicator_url' } else { 'youtube_url' }
    $txt = if ($kind -eq 'indicator') {
      ('Manual indicator ingest from YouTube URL. source_ref=' + $u + ' video_id=' + $vid)
    } else {
      ('Manual concept ingest from YouTube URL. source_ref=' + $u + ' video_id=' + $vid)
    }

    $resolverRaw = (python scripts/pipeline/transcript_resolver.py --video-id $vid --url $u) -join "`n"
    $resolver = $null
    try { $resolver = $resolverRaw | ConvertFrom-Json } catch { $resolver = $null }
    if ($null -ne $resolver -and $resolver.ok -eq $true -and -not [string]::IsNullOrWhiteSpace([string]$resolver.text)) {
      $txt = [string]$resolver.text
      if ([string]$resolver.quality -eq 'caption') {
        $srcType = if ($kind -eq 'indicator') { 'transcript_indicator' } else { 'transcript' }
      } elseif ([string]$resolver.quality -eq 'auto_caption') {
        $srcType = if ($kind -eq 'indicator') { 'auto_transcript_indicator' } else { 'auto_transcript' }
      } elseif ([string]$resolver.quality -eq 'asr') {
        $srcType = if ($kind -eq 'indicator') { 'asr_transcript_indicator' } else { 'asr_transcript' }
      }
    }

    $rcRaw = (python scripts/pipeline/emit_research_card.py --source-ref $u --source-type $srcType --raw-text $txt --title $vid --author 'manual-youtube') -join "`n"
    $rc = $rcRaw | ConvertFrom-Json
    $lmRaw = (python scripts/pipeline/link_research_indicators.py --research-card-path $rc.research_card_path --indicator-record-paths '[]') -join "`n"
    $lm = $lmRaw | ConvertFrom-Json

    $day = (Get-Date).ToUniversalTime().ToString('yyyyMMdd')
    $bdir = Join-Path 'artifacts/bundles' $day
    if (-not (Test-Path $bdir)) { New-Item -ItemType Directory -Path $bdir | Out-Null }
    $bpath = (Join-Path $bdir ($vid + '.bundle.json')).Replace('\\','/')
    $transcriptError = 'TRANSCRIPT_UNAVAILABLE_AT_INGEST'
    if ($null -ne $resolver -and $resolver.ok -eq $true) { $transcriptError = '' }
    $bundle = [ordered]@{
      id = ('bundle_' + $vid)
      created_at = [DateTime]::UtcNow.ToString('o')
      source = $(if ($kind -eq 'indicator') { 'youtube_manual_indicator' } else { 'youtube_manual' })
      source_ref = $u
      research_card_path = [string]$rc.research_card_path
      linkmap_path = [string]$lm.linkmap_path
      indicator_record_paths = @()
      status = 'NEW'
      attempts = 0
      transcript_method = $(if ($null -ne $resolver) { [string]$resolver.method } else { 'none' })
      transcript_quality = $(if ($null -ne $resolver) { [string]$resolver.quality } else { 'none' })
      last_error = $transcriptError
    }
    ($bundle | ConvertTo-Json -Depth 8) | Set-Content -Path $bpath -Encoding utf8

    if ($bundleIndex -notcontains $bpath) { $bundleIndex = @($bpath) + @($bundleIndex) }
    $added += 1
  }

  ($bundleIndex | ConvertTo-Json -Depth 6) | Set-Content -Path $bundleIndexPath -Encoding utf8
  Write-Output ("Ingested " + $added + " videos (concepts=" + $conceptUrls.Count + ", indicators=" + $indicatorUrls.Count + "). Say 'run lab now' to process.")
}

function Invoke-NoodleReadonly {
  param([string]$InputMessage,[string]$InputLower,[string]$ChatId)

  if ($InputLower -match '^\s*noodle\s+reset\s*$') {
    try {
      $stateDir = Join-RepoPath 'data/state'
      if (Test-Path $stateDir) {
        $keep = @('noodle_retrieval.json','noodle_aliases.json')
        Get-ChildItem -Path $stateDir -File -Filter 'noodle_*.json' -ErrorAction SilentlyContinue |
          Where-Object { $keep -notcontains $_.Name } |
          Remove-Item -Force -ErrorAction SilentlyContinue
      }
    } catch {}
    Send-NoodleReply -ChatId $ChatId -ReplyText 'Noodle reset. (Read-only; no knowledge deleted.)'
    return
  }

  $blockedWrite = @('idea','insight','concept:','save','record','update doctrine','run','build','apply')
  foreach ($kw in $blockedWrite) {
    if ($InputLower -like ('*' + $kw + '*')) {
      Send-NoodleReply -ChatId $ChatId -ReplyText 'Noodle is read-only in this chat. Use the main oQ chat for saves or running the pipeline.'
      return
    }
  }

  $privacyPatterns = @(
    'token','tokens','key','keys','auth','secret','password','api key',
    'private user info','other chat content','local file path','config secret','show me your tokens'
  )
  foreach ($p in $privacyPatterns) {
    if ($InputLower -like ('*' + $p + '*')) {
      Send-NoodleReply -ChatId $ChatId -ReplyText "Can't share that here."
      return
    }
  }

  # Always load doctrine for Noodle read-only retrieval baseline.
  $doctrinePath = Join-RepoPath 'docs/DOCTRINE/analyser-doctrine.md'
  $doctrineLoaded = $false
  if (Test-Path $doctrinePath) {
    try {
      [void](Get-Content $doctrinePath -Raw)
      $doctrineLoaded = $true
    } catch {
      $doctrineLoaded = $false
    }
  }

  $retrievalCfg = Get-NoodleRetrievalConfig
  if (Try-HandleNoodleLearningQueries -InputLower $InputLower -Config $retrievalCfg -ChatId $ChatId) {
    return
  }

  $packPath = Join-RepoPath 'artifacts/thesis_packs/20260226/michaelionita-last10.automation_thesis_pack.json'
  if (($InputLower -like '*michael*') -and ($InputLower -like '*last*10*') -and (Test-Path $packPath)) {
    try {
      $pack = Get-Content $packPath -Raw | ConvertFrom-Json
      $ideas = @($pack.key_ideas | Select-Object -First 5)
      $hooks = @($pack.trading_relevant_concept_hooks | Select-Object -First 3)
      $parts = @('Noodle notes (read-only, evidence-first):')
      foreach ($x in $ideas) { $parts += ('- signal: ' + [string]$x) }
      foreach ($h in $hooks) { $parts += ('- hook: ' + [string]$h) }
      $parts += '- assumption: concept frequency != live edge; treat as hypothesis only.'
      $parts += '- uncertainty: transcript quality/context limits may hide nuance.'
      $parts += 'Q1) Which hook should we pressure-test first: session gating or execution-quality telemetry?'
      $parts += 'Q2) Want me to map these into a strict test checklist (still read-only)?'
      Send-NoodleReply -ChatId $ChatId -ReplyText ($parts -join "`n")
      return
    } catch {
      $parts = @(
        'Noodle is in read-only mode and could not load the referenced pack cleanly.',
        'Q1) Share a thesis/research artifact path to inspect?',
        'Q2) Should I summarise doctrine heuristics only?'
      )
      Send-NoodleReply -ChatId $ChatId -ReplyText ($parts -join "`n")
      return
    }
  }

  if ($InputLower -like '*doctrine*' -and (Test-Path (Join-RepoPath 'docs/DOCTRINE/analyser-doctrine.md'))) {
    $lines = Get-Content (Join-RepoPath 'docs/DOCTRINE/analyser-doctrine.md') | Where-Object { $_ -match '^- \[' } | Select-Object -First 6
    $parts = @('Noodle doctrine skim (read-only):')
    foreach ($l in $lines) {
      $clean = ($l -replace '^- \[[^\]]+\]\s*','').Trim()
      $parts += ('- ' + $clean)
    }
    $parts += '- uncertainty: this is compact guidance, not full transcript evidence.'
    $parts += 'Q1) Want research heuristics or automation heuristics next?'
    Send-NoodleReply -ChatId $ChatId -ReplyText ($parts -join "`n")
    return
  }

  $fallback = @(
    'Noodle is read-only here: I can summarise referenced thesis/research/doctrine artifacts only.',
    'Q1) Which artifact path should I inspect?'
  )
  Send-NoodleReply -ChatId $ChatId -ReplyText ($fallback -join "`n")
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
$routeRecord = Get-TelegramChatRoute -TargetChatId $ChatId
if ($null -ne $routeRecord -and [string]$routeRecord.mode -eq 'ANALYSER_READONLY') {
  # Noodle must respond to any normal group message in this chat route.
  # Do not require reply context/message-id presence.
  $safeMessage = if ([string]::IsNullOrWhiteSpace($Message)) { 'help' } else { $Message }
  $safeLower = $safeMessage.ToLowerInvariant().Trim()

  $rrun = 'route-noodle-' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  Emit-LogEvent -RunId $rrun -StatusWord 'INFO' -StatusEmoji 'ℹ️' -ReasonCode 'ROUTE_ANALYSER_READONLY' -Summary ('chat routed to ANALYSER_READONLY: ' + [string]$ChatId) -Inputs @($safeMessage) -Outputs @('ANALYSER_READONLY')
  Invoke-NoodleReadonly -InputMessage $safeMessage -InputLower $safeLower -ChatId $ChatId
  exit 0
}

$route = 'BUILD_PATH'
$rule = 'default_unsure_to_build'
$intentMatch = $null
$intentAction = ''
$intentName = ''
$buildQuestion = $Message

if ($m -match '^retry\s+insight\s+.+$') {
  $route = 'FAST_PATH'
  $rule = 'explicit_retry_insight'
  $intentAction = 'retry_insight'
}
if ($m -match '^ingest\s+(concepts|indicators|videos)\b') {
  $route = 'FAST_PATH'
  $rule = 'manual_video_ingest'
  $intentAction = 'manual_video_ingest'
}
if ($m -eq 'run lab now' -or $m -eq 'lab status' -or $m -eq 'lab report' -or $m -eq 'run autopilot now') {
  $route = 'FAST_PATH'
  $rule = 'lab_command_surface'
  $intentAction = 'lab_surface'
}
if ($m -match '^(idea|insight|concept)\s*$') {
  $route = 'FAST_PATH'
  $rule = 'explicit_empty_insight_keyword'
  $intentAction = 'emit_insight_card'
}

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

if ($rule -ne 'clarifier_change_it' -and $rule -ne 'clarifier_just_explain' -and [string]::IsNullOrWhiteSpace($intentAction)) {
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

  if ($m -match '^ingest\s+concepts\b') {
    Invoke-ManualVideoIngest -Message $Message -Mode 'concepts'
    exit 0
  }
  if ($m -match '^ingest\s+indicators\b') {
    Invoke-ManualVideoIngest -Message $Message -Mode 'indicators'
    exit 0
  }
  if ($m -match '^ingest\s+videos\b') {
    Invoke-ManualVideoIngest -Message $Message -Mode 'mixed'
    exit 0
  }

  if ($m -eq 'run lab now' -or $m -eq 'run autopilot now') {
    $lab = (powershell -ExecutionPolicy Bypass -File scripts/pipeline/autopilot_worker.ps1 -MaxBundlesPerRun 3) -join "`n"
    $labObj = $null
    try { $labObj = $lab | ConvertFrom-Json } catch { $labObj = $null }
    if ($null -ne $labObj) {
      Write-Output ("Lab run complete: bundles=" + [string]$labObj.bundles_processed + ", promotions=" + [string]$labObj.promotions_processed + ", refinements=" + [string]$labObj.refinements_run + ", errors=" + [string]$labObj.errors_count)
    } else {
      Write-Output 'Lab run complete.'
    }
    exit 0
  }

  if ($m -eq 'lab status') {
    $autoPath = 'data/state/autopilot_summary.json'
    $auto = $null
    if (Test-Path $autoPath) { try { $auto = Get-Content $autoPath -Raw | ConvertFrom-Json } catch { $auto = $null } }
    $bundleNewCount = 0
    $bundleIndexPath = 'artifacts/bundles/INDEX.json'
    if (Test-Path $bundleIndexPath) {
      try {
        $bundlePaths = @(Get-Content $bundleIndexPath -Raw | ConvertFrom-Json)
        foreach ($bp in $bundlePaths) {
          if (-not (Test-Path -LiteralPath $bp)) { continue }
          try {
            $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
            if ($b.status -eq 'NEW') { $bundleNewCount += 1 }
          } catch {}
        }
      } catch {}
    }
    if ($null -eq $auto) {
      Write-Output ("Lab status: no recent summary. bundles_new=" + $bundleNewCount)
    } else {
      Write-Output ("Lab status: bundles=" + [string]$auto.bundles_processed + ", promotions=" + [string]$auto.promotions_processed + ", refinements=" + [string]$auto.refinements_run + ", errors=" + [string]$auto.errors_count + ", bundles_new=" + $bundleNewCount)
    }
    exit 0
  }

  if ($intentAction -eq 'emit_insight_card') {
    $concept = ''
    if ($Message -match '^\s*(?:idea|insight|concept)\s+(.+)$') {
      $concept = $matches[1].Trim()
    }
    if ([string]::IsNullOrWhiteSpace($concept)) {
      Write-Output 'Idea rejected: add text after idea/insight/concept.'
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

  if ($intentAction -eq 'retry_insight') {
    $insightId = ''
    if ($Message -match '^\s*retry\s+insight\s+(.+)$') {
      $insightId = $matches[1].Trim()
    }
    if ([string]::IsNullOrWhiteSpace($insightId)) {
      Write-Output 'Provide an insight id (retry insight <id>).'
      exit 0
    }

    $indexPath = 'artifacts/insights/INDEX.json'
    if (-not (Test-Path $indexPath)) {
      Write-Output 'Insight not found.'
      exit 0
    }

    $paths = @()
    try { $paths = @(Get-Content $indexPath -Raw | ConvertFrom-Json) } catch { $paths = @() }
    $found = $false
    foreach ($p in $paths) {
      if (-not (Test-Path -LiteralPath $p)) { continue }
      try {
        $card = Get-Content -LiteralPath $p -Raw | ConvertFrom-Json
        $cardId = ([string]$card.id).Trim().ToLowerInvariant()
        $targetId = ([string]$insightId).Trim().ToLowerInvariant()
        if ($cardId -eq $targetId -or [IO.Path]::GetFileNameWithoutExtension([string]$p).StartsWith($targetId)) {
          $card.status = 'NEW'
          $card.last_error = $null
          ($card | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $p -Encoding utf8
          $found = $true
          break
        }
      } catch {}
    }

    if ($found) {
      Emit-LogEvent -RunId ($runId + '-retry-insight') -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'INSIGHT_RETRY_QUEUED' -Summary 'Insight reset to NEW for retry' -Inputs @($insightId) -Outputs @('status=NEW')
      Write-Output 'Insight retry queued.'
    } else {
      Write-Output 'Insight not found.'
    }
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

    $bundleNewCount = 0
    $bundleIndexPath = 'artifacts/bundles/INDEX.json'
    if (Test-Path $bundleIndexPath) {
      try {
        $bundlePaths = @(Get-Content $bundleIndexPath -Raw | ConvertFrom-Json)
        foreach ($bp in $bundlePaths) {
          if (-not (Test-Path -LiteralPath $bp)) { continue }
          try {
            $b = Get-Content -LiteralPath $bp -Raw | ConvertFrom-Json
            if ($b.status -eq 'NEW') { $bundleNewCount += 1 }
          } catch {}
        }
      } catch {}
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
    Write-Output ("Queue: bundles_new=" + [string]$bundleNewCount)
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


