<#
.SYNOPSIS
Wrapper to emit deterministic Oragorn ActionEvents via scripts/log_event.py.

.EXAMPLE
./scripts/automation/oragorn_action_wrapper.ps1 -Action delegate -Summary "Delegated parser fix" -Inputs ticket-123 -Outputs agent:parser

.EXAMPLE
./scripts/automation/oragorn_action_wrapper.ps1 -Action diagnose -Summary "Root cause identified" -StatusWord WARN -ReasonCode INVESTIGATION_COMPLETE

.EXAMPLE
./scripts/automation/oragorn_action_wrapper.ps1 -Action spawn -Summary "Spawned subagent" -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('delegate', 'spawn', 'diagnose', 'context-update')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Summary,

    [ValidateSet('OK', 'WARN', 'FAIL', 'INFO', 'BLOCKED')]
    [string]$StatusWord = 'OK',

    [string]$ReasonCode,

    [string[]]$Inputs = @(),

    [string[]]$Outputs = @(),

    [string]$RunId,

    [string]$ModelId = 'gpt-5.3-codex',

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$actionMap = @{
    'delegate'       = 'DELEGATION_SENT'
    'spawn'          = 'SUBAGENT_SPAWNED'
    'diagnose'       = 'DIAGNOSIS_COMPLETE'
    'context-update' = 'CONTEXT_UPDATE'
}

$statusEmojiMap = @{
    'OK'      = '✅'
    'WARN'    = '⚠️'
    'FAIL'    = '❌'
    'INFO'    = 'ℹ️'
    'BLOCKED' = '⛔'
}

$emittedAction = $actionMap[$Action]
if (-not $emittedAction) {
    throw "Unsupported action: $Action"
}

if (-not $RunId -or [string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = [guid]::NewGuid().ToString()
}

if (-not $ReasonCode -or [string]::IsNullOrWhiteSpace($ReasonCode)) {
    $ReasonCode = $emittedAction
}

$statusWordUpper = $StatusWord.ToUpperInvariant()
$statusEmoji = $statusEmojiMap[$statusWordUpper]
if (-not $statusEmoji) {
    throw "Unsupported StatusWord for emoji mapping: $StatusWord"
}

# Resolve workspace root robustly from script location: <root>/scripts/automation/this.ps1
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$logEventPath = Join-Path $workspaceRoot 'scripts\log_event.py'
if (-not (Test-Path -LiteralPath $logEventPath)) {
    throw "Cannot find log_event.py at expected path: $logEventPath"
}

$argList = @(
    $logEventPath,
    '--run-id', $RunId,
    '--agent', 'Oragorn',
    '--action', $emittedAction,
    '--status-word', $statusWordUpper,
    '--status-emoji', $statusEmoji,
    '--model-id', $ModelId,
    '--summary', $Summary,
    '--reason-code', $ReasonCode
)

if ($Inputs.Count -gt 0) {
    $argList += '--inputs'
    $argList += $Inputs
}

if ($Outputs.Count -gt 0) {
    $argList += '--outputs'
    $argList += $Outputs
}

$displayCommand = 'python ' + ($argList | ForEach-Object {
    if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
}) -join ' '

if ($DryRun) {
    Write-Host "[DryRun] cwd=$workspaceRoot"
    Write-Host "[DryRun] $displayCommand"
    exit 0
}

Push-Location -LiteralPath $workspaceRoot
try {
    & python @argList
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($exitCode -ne 0) {
    Write-Error "log_event.py emit failed with exit code $exitCode"
    exit $exitCode
}

Write-Host "OK run_id=$RunId action=$emittedAction"
exit 0
