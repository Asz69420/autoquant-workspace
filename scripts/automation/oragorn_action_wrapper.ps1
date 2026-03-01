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
    [ValidateSet('delegate', 'spawn', 'spawn-finish', 'spawn-fail', 'diagnose', 'context-update')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Summary,

    [ValidateSet('START', 'OK', 'WARN', 'FAIL', 'INFO', 'BLOCKED')]
    [string]$StatusWord = 'OK',

    [ValidateSet('OK', 'WARN', 'FAIL')]
    [string]$Status,

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
    'spawn'          = 'SUBAGENT_SPAWN'
    'spawn-finish'   = 'SUBAGENT_FINISH'
    'spawn-fail'     = 'SUBAGENT_FAIL'
    'diagnose'       = 'DIAGNOSIS_COMPLETE'
    'context-update' = 'CONTEXT_UPDATE'
}

$statusEmojiMap = @{
    'START'   = '▶️'
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

if ($Action -eq 'spawn' -and $PSBoundParameters.ContainsKey('Status')) {
    switch ($Status) {
        'OK' {
            $emittedAction = 'SUBAGENT_FINISH'
            $StatusWord = 'OK'
        }
        'WARN' {
            $emittedAction = 'SUBAGENT_FINISH'
            $StatusWord = 'WARN'
        }
        'FAIL' {
            $emittedAction = 'SUBAGENT_FAIL'
            $StatusWord = 'FAIL'
        }
    }
}

if (-not $RunId -or [string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = [guid]::NewGuid().ToString()
}

if (-not $PSBoundParameters.ContainsKey('StatusWord') -and -not $PSBoundParameters.ContainsKey('Status')) {
    switch ($Action) {
        'spawn' { $StatusWord = 'START' }
        'spawn-finish' { $StatusWord = 'OK' }
        'spawn-fail' { $StatusWord = 'FAIL' }
        default { }
    }
}

if (-not $ReasonCode -or [string]::IsNullOrWhiteSpace($ReasonCode)) {
    $ReasonCode = $emittedAction
}

$statusWordUpper = $StatusWord.ToUpperInvariant()
$statusEmoji = $statusEmojiMap[$statusWordUpper]
if (-not $statusEmoji) {
    throw "Unsupported StatusWord for emoji mapping: $StatusWord"
}

if ($Action -like 'spawn*' -and $Inputs.Count -eq 0) {
    $Inputs = @('sessions_spawn')
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
