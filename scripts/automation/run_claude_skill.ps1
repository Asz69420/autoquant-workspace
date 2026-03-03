[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('research', 'generate', 'doctrine', 'audit')]
  [string]$Mode,

  [string]$PromptFile,

  [int]$RetryCount = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$policyPath = Join-Path $workspaceRoot 'config\claude_skill_policy.json'
$logEventPath = Join-Path $workspaceRoot 'scripts\log_event.py'
$logsDir = Join-Path $workspaceRoot 'data\logs\claude-skill'

if (-not (Test-Path -LiteralPath $policyPath)) {
  throw "Missing policy file: $policyPath"
}
if (-not (Test-Path -LiteralPath $logEventPath)) {
  throw "Missing logger script: $logEventPath"
}

$policy = Get-Content -LiteralPath $policyPath -Encoding UTF8 | ConvertFrom-Json
$allowedModes = @($policy.allowed_modes)
if ($allowedModes.Count -eq 0) {
  throw 'Policy allowed_modes is empty.'
}
if ($allowedModes -notcontains $Mode) {
  throw "Mode '$Mode' is not allowed by policy."
}

$effectiveRetryCount = $RetryCount
if ($effectiveRetryCount -lt 1) {
  if ($policy.default_retry_count -and [int]$policy.default_retry_count -gt 0) {
    $effectiveRetryCount = [int]$policy.default_retry_count
  }
  else {
    $effectiveRetryCount = 1
  }
}

$timeoutSeconds = 900
if ($policy.timeout_seconds -and [int]$policy.timeout_seconds -gt 0) {
  $timeoutSeconds = [int]$policy.timeout_seconds
}

$modelId = 'claude-sonnet-4-5'
if (-not [string]::IsNullOrWhiteSpace([string]$policy.model_preference)) {
  $modelId = [string]$policy.model_preference
}

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

function Get-DefaultPrompt {
  param([string]$SkillMode)

  switch ($SkillMode) {
    'research' {
      return "MODE: RESEARCH`nPerform research against repository context and produce concise, evidence-backed findings."
    }
    'generate' {
      return "MODE: GENERATE`nGenerate requested artifacts in the workspace with clear assumptions and constraints."
    }
    'doctrine' {
      return "MODE: DOCTRINE`nSynthesize and refine doctrine notes into actionable, non-duplicative guidance."
    }
    'audit' {
      return "MODE: AUDIT`nAudit recent outputs for quality/risk issues and summarize concrete remediation steps."
    }
    default {
      return "MODE: $SkillMode"
    }
  }
}

function Test-IsRateLimited {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }

  $patterns = @(
    'rate\s*limit',
    'too\s*many\s*requests',
    '\b429\b',
    'quota',
    'temporar(?:y|ily)\s+unavailable',
    'overloaded',
    'try\s+again\s+later',
    'resource\s+exhausted',
    'throttl'
  )

  foreach ($p in $patterns) {
    if ($Text -match "(?i)$p") { return $true }
  }

  return $false
}

function Get-BackoffSeconds {
  param([int]$Attempt)

  $base = 20
  $seconds = $base * $Attempt * $Attempt
  if ($seconds -gt 180) { $seconds = 180 }
  if ($seconds -lt 10) { $seconds = 10 }
  return $seconds
}

function Emit-ActionEvent {
  param(
    [string]$RunId,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$Summary,
    [string]$ReasonCode,
    [string[]]$Inputs,
    [string[]]$Outputs,
    [int]$Attempt
  )

  $args = @(
    $logEventPath,
    '--run-id', $RunId,
    '--agent', 'claude-skill',
    '--action', ('claude_skill_' + $Mode),
    '--status-word', $StatusWord,
    '--status-emoji', $StatusEmoji,
    '--model-id', $modelId,
    '--summary', $Summary
  )

  if (-not [string]::IsNullOrWhiteSpace($ReasonCode)) {
    $args += @('--reason-code', $ReasonCode)
  }
  if ($Attempt -gt 0) {
    $args += @('--attempt', [string]$Attempt)
  }
  if ($Inputs -and $Inputs.Count -gt 0) {
    $args += '--inputs'
    $args += $Inputs
  }
  if ($Outputs -and $Outputs.Count -gt 0) {
    $args += '--outputs'
    $args += $Outputs
  }

  $old = $ErrorActionPreference
  $ErrorActionPreference = 'SilentlyContinue'
  Push-Location -LiteralPath $workspaceRoot
  try {
    & python @args 2>$null | Out-Null
  }
  finally {
    Pop-Location
    $ErrorActionPreference = $old
  }
}

function Invoke-ClaudeAttempt {
  param(
    [string]$PromptText,
    [string]$Model,
    [int]$TimeoutSec,
    [string]$AllowedTools
  )

  $stdOutPath = [System.IO.Path]::GetTempFileName()
  $stdErrPath = [System.IO.Path]::GetTempFileName()
  $timedOut = $false

  try {
    Push-Location -LiteralPath $workspaceRoot
    $proc = Start-Process -FilePath 'claude' -ArgumentList @('-p', $PromptText, '--model', $Model, '--allowedTools', $AllowedTools) -NoNewWindow -PassThru -RedirectStandardOutput $stdOutPath -RedirectStandardError $stdErrPath

    Wait-Process -Id $proc.Id -Timeout $TimeoutSec -ErrorAction SilentlyContinue
    if (-not $proc.HasExited) {
      $timedOut = $true
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    $stdout = ''
    $stderr = ''
    if (Test-Path -LiteralPath $stdOutPath) {
      $stdout = Get-Content -LiteralPath $stdOutPath -Raw -Encoding UTF8
    }
    if (Test-Path -LiteralPath $stdErrPath) {
      $stderr = Get-Content -LiteralPath $stdErrPath -Raw -Encoding UTF8
    }

    $exitCode = if ($timedOut) { 124 } else { [int]$proc.ExitCode }

    return [pscustomobject]@{
      exit_code = $exitCode
      stdout = $stdout
      stderr = $stderr
      timed_out = $timedOut
    }
  }
  finally {
    Pop-Location
    Remove-Item -LiteralPath $stdOutPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stdErrPath -Force -ErrorAction SilentlyContinue
  }
}

$promptText = ''
$inputs = @("mode=$Mode")
if (-not [string]::IsNullOrWhiteSpace($PromptFile)) {
  $promptPath = $PromptFile
  if (-not [System.IO.Path]::IsPathRooted($promptPath)) {
    $promptPath = Join-Path $workspaceRoot $promptPath
  }
  $promptPath = (Resolve-Path -LiteralPath $promptPath).Path
  $promptText = Get-Content -LiteralPath $promptPath -Raw -Encoding UTF8
  $inputs += ('prompt=' + ($promptPath.Replace('\\', '/')))
}
else {
  $promptText = Get-DefaultPrompt -SkillMode $Mode
}

if ([string]::IsNullOrWhiteSpace($promptText)) {
  throw 'Prompt text is empty.'
}

$allowedTools = 'Read,Write,Bash(python scripts/log_event.py*)'
if ($Mode -eq 'research') {
  $allowedTools = 'Read,Write,Bash(python scripts/log_event.py*),Bash(python scripts/quandalf/build_index.py*)'
}

$runId = ('claude-skill-' + $Mode + '-' + [DateTimeOffset]::UtcNow.ToString('yyyyMMddHHmmss') + '-' + ([guid]::NewGuid().ToString('N').Substring(0, 6)))
$ts = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logPath = Join-Path $logsDir ("$Mode-$ts.log")
$resultPath = Join-Path $logsDir ("$Mode-$ts.result.json")

Emit-ActionEvent -RunId $runId -StatusWord 'START' -StatusEmoji '▶️' -Summary "Claude skill start mode=$Mode" -ReasonCode 'CLAUDE_SKILL_START' -Inputs $inputs -Outputs @(($logPath.Replace('\\', '/'))) -Attempt 1

$final = $null
$attemptsUsed = 0
$lastRateLimited = $false

for ($attempt = 1; $attempt -le $effectiveRetryCount; $attempt++) {
  $attemptsUsed = $attempt
  $response = $null
  try {
    $response = Invoke-ClaudeAttempt -PromptText $promptText -Model $modelId -TimeoutSec $timeoutSeconds -AllowedTools $allowedTools
  }
  catch {
    $response = [pscustomobject]@{
      exit_code = 1
      stdout = ''
      stderr = ([string]$_)
      timed_out = $false
    }
  }

  $combined = (($response.stdout + "`n" + $response.stderr).Trim())
  $isRateLimited = Test-IsRateLimited -Text $combined
  $lastRateLimited = $isRateLimited

  $attemptLog = @(
    "=== attempt $attempt / $effectiveRetryCount ===",
    "exit_code=$($response.exit_code)",
    "timed_out=$($response.timed_out)",
    "rate_limited=$isRateLimited",
    '',
    '--- stdout ---',
    $response.stdout,
    '',
    '--- stderr ---',
    $response.stderr,
    ''
  ) -join "`r`n"

  Add-Content -LiteralPath $logPath -Value $attemptLog -Encoding UTF8

  if ($response.exit_code -eq 0) {
    Emit-ActionEvent -RunId $runId -StatusWord 'OK' -StatusEmoji '✅' -Summary "Claude skill completed mode=$Mode attempt=$attempt" -ReasonCode 'CLAUDE_SKILL_OK' -Inputs $inputs -Outputs @(($logPath.Replace('\\', '/'))) -Attempt $attempt
    $final = [pscustomobject]@{
      ok = $true
      mode = $Mode
      run_id = $runId
      attempts_used = $attempt
      retry_count = $effectiveRetryCount
      exit_code = 0
      rate_limited = $false
      timed_out = $false
      log_path = ($logPath.Replace('\\', '/'))
      summary = "completed"
    }
    break
  }

  if ($isRateLimited -and $attempt -lt $effectiveRetryCount) {
    $backoffSeconds = Get-BackoffSeconds -Attempt $attempt
    Emit-ActionEvent -RunId $runId -StatusWord 'THROTTLED' -StatusEmoji '⚠️' -Summary "Claude skill rate-limited mode=$Mode attempt=$attempt backoff=${backoffSeconds}s" -ReasonCode 'CLAUDE_SKILL_RATE_LIMIT' -Inputs $inputs -Outputs @(($logPath.Replace('\\', '/'))) -Attempt $attempt
    Emit-ActionEvent -RunId $runId -StatusWord 'RETRY' -StatusEmoji '🔁' -Summary "Claude skill retry scheduled mode=$Mode next_attempt=$($attempt + 1)" -ReasonCode 'CLAUDE_SKILL_RETRY' -Inputs $inputs -Outputs @(($logPath.Replace('\\', '/'))) -Attempt $attempt
    Start-Sleep -Seconds $backoffSeconds
    continue
  }

  $reasonCode = if ($response.timed_out) { 'CLAUDE_SKILL_TIMEOUT' } elseif ($isRateLimited) { 'CLAUDE_SKILL_RATE_LIMIT_EXHAUSTED' } else { 'CLAUDE_SKILL_EXEC_FAIL' }
  Emit-ActionEvent -RunId $runId -StatusWord 'FAIL' -StatusEmoji '❌' -Summary "Claude skill failed mode=$Mode attempt=$attempt exit=$($response.exit_code)" -ReasonCode $reasonCode -Inputs $inputs -Outputs @(($logPath.Replace('\\', '/'))) -Attempt $attempt

  $final = [pscustomobject]@{
    ok = $false
    mode = $Mode
    run_id = $runId
    attempts_used = $attempt
    retry_count = $effectiveRetryCount
    exit_code = [int]$response.exit_code
    rate_limited = $isRateLimited
    timed_out = [bool]$response.timed_out
    log_path = ($logPath.Replace('\\', '/'))
    summary = 'failed'
  }
  break
}

if ($null -eq $final) {
  $final = [pscustomobject]@{
    ok = $false
    mode = $Mode
    run_id = $runId
    attempts_used = $attemptsUsed
    retry_count = $effectiveRetryCount
    exit_code = 1
    rate_limited = $lastRateLimited
    timed_out = $false
    log_path = ($logPath.Replace('\\', '/'))
    summary = 'failed-no-final-state'
  }
}

$final | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding UTF8

$payload = [pscustomobject]@{
  ok = [bool]$final.ok
  mode = [string]$final.mode
  run_id = [string]$final.run_id
  attempts_used = [int]$final.attempts_used
  retry_count = [int]$final.retry_count
  exit_code = [int]$final.exit_code
  rate_limited = [bool]$final.rate_limited
  timed_out = [bool]$final.timed_out
  log_path = [string]$final.log_path
  result_path = ($resultPath.Replace('\\', '/'))
  summary = [string]$final.summary
}

$payload | ConvertTo-Json -Depth 6

if ($payload.ok) {
  exit 0
}

exit 1
