[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('research', 'generate', 'doctrine', 'audit')]
  [string]$Mode,

  [string]$PromptFile,

  [int]$RetryCount = 1,

  [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runnerPath = Join-Path $workspaceRoot 'scripts\automation\run_claude_skill.ps1'

if (-not (Test-Path -LiteralPath $runnerPath)) {
  throw "Missing runner script: $runnerPath"
}

$args = @{
  Mode = $Mode
  RetryCount = $RetryCount
}

if (-not [string]::IsNullOrWhiteSpace($PromptFile)) {
  $args.PromptFile = $PromptFile
}

$raw = & powershell -NoProfile -ExecutionPolicy Bypass -File $runnerPath @args
$exitCode = $LASTEXITCODE

$jsonText = ($raw | Out-String).Trim()
$result = $null

try {
  $result = $jsonText | ConvertFrom-Json -ErrorAction Stop
}
catch {
  $result = [pscustomobject]@{
    ok = $false
    mode = $Mode
    run_id = ''
    attempts_used = 0
    retry_count = $RetryCount
    exit_code = $exitCode
    rate_limited = $false
    timed_out = $false
    log_path = ''
    result_path = ''
    summary = 'runner-output-not-json'
  }
}

if ($AsJson) {
  $result | ConvertTo-Json -Depth 6
}
else {
  $status = if ($result.ok) { 'OK' } else { 'FAIL' }
  Write-Output ("SKILL_STATUS=$status")
  Write-Output ("SKILL_MODE=$($result.mode)")
  Write-Output ("SKILL_RUN_ID=$($result.run_id)")
  Write-Output ("SKILL_ATTEMPTS=$($result.attempts_used)")
  Write-Output ("SKILL_EXIT_CODE=$($result.exit_code)")
  Write-Output ("SKILL_RATE_LIMITED=$($result.rate_limited)")
  Write-Output ("SKILL_TIMED_OUT=$($result.timed_out)")
  Write-Output ("SKILL_LOG_PATH=$($result.log_path)")
  Write-Output ("SKILL_RESULT_PATH=$($result.result_path)")
  Write-Output ("SKILL_SUMMARY=$($result.summary)")
}

if ($result.ok) {
  exit 0
}

if ($exitCode -ne 0) {
  exit $exitCode
}

exit 1
