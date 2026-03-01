<#
.SYNOPSIS
Oragorn spawn wrapper with enforced lifecycle logging.

.DESCRIPTION
This script enforces parent-owned sub-agent lifecycle logging around spawn execution.
Order is strict:
1) Emit SUBAGENT_SPAWN first via oragorn_action_wrapper.ps1.
2) Execute the spawn command.
3) Emit terminal lifecycle via SUBAGENT_FINISH or SUBAGENT_FAIL.

If no spawn command path is available, this script fails closed (BLOCKED).
Do not call sessions_spawn directly from delegation logic.

.EXAMPLE
# Preferred when sessions_spawn is available on PATH
./scripts/automation/oragorn_spawn.ps1 -Summary "Spawn verifier" -TaskDescription "Run QC verifier"

.EXAMPLE
# Explicit command path (pluggable fallback)
./scripts/automation/oragorn_spawn.ps1 -Summary "Spawn worker" -TaskDescription "Implement patch" -SpawnCommand openclaw -SpawnArgs @('agent','--to','@target','--message','do task')

.EXAMPLE
# Safe demonstration only (no logs written, no spawn executed)
./scripts/automation/oragorn_spawn.ps1 -Summary "Dry run" -TaskDescription "Show command and lifecycle" -SpawnCommand openclaw -SpawnArgs @('sessions','--json') -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Summary,

    [Parameter(Mandatory = $true)]
    [string]$TaskDescription,

    [string[]]$SpawnCommand,

    [string[]]$SpawnArgs = @(),

    [string]$ModelId = 'gpt-5.3-codex',

    [string]$RunId = ([guid]::NewGuid().ToString()),

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wrapperPath = Join-Path $PSScriptRoot 'oragorn_action_wrapper.ps1'
if (-not (Test-Path -LiteralPath $wrapperPath)) {
    throw "Missing required wrapper: $wrapperPath"
}

function Format-CommandDisplay {
    param([string[]]$CommandParts)

    return ($CommandParts | ForEach-Object {
        if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' }
        else { $_ }
    }) -join ' '
}

function Invoke-OragornLifecycle {
    param(
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$LifecycleSummary,
        [Parameter(Mandatory = $true)][string[]]$Inputs,
        [string[]]$Outputs = @(),
        [string]$StatusWord,
        [string]$ReasonCode,
        [switch]$UseDryRun
    )

    $wrapperParams = @{
        Action  = $Action
        Summary = $LifecycleSummary
        RunId   = $RunId
        ModelId = $ModelId
        Inputs  = $Inputs
    }

    if ($Outputs.Count -gt 0) {
        $wrapperParams['Outputs'] = $Outputs
    }

    if ($StatusWord) {
        $wrapperParams['StatusWord'] = $StatusWord
    }

    if ($ReasonCode) {
        $wrapperParams['ReasonCode'] = $ReasonCode
    }

    if ($UseDryRun) {
        $wrapperParams['DryRun'] = $true
    }

    & $wrapperPath @wrapperParams
    if ($LASTEXITCODE -ne 0) {
        throw "oragorn_action_wrapper failed ($Action) with exit code $LASTEXITCODE"
    }
}

$resolvedCommand = @()
if ($SpawnCommand -and $SpawnCommand.Count -gt 0) {
    $resolvedCommand = @($SpawnCommand + $SpawnArgs)
}
else {
    $sessionsSpawn = Get-Command -Name 'sessions_spawn' -ErrorAction SilentlyContinue
    if ($sessionsSpawn) {
        $resolvedCommand = @($sessionsSpawn.Name) + $SpawnArgs
    }
}

$commandIsAvailable = ($resolvedCommand.Count -gt 0)
$commandDisplay = if ($commandIsAvailable) { Format-CommandDisplay -CommandParts $resolvedCommand } else { '<none>' }
$startInputs = @("task:$TaskDescription", "spawn_cmd:$commandDisplay")

# Lifecycle START must be emitted first.
Invoke-OragornLifecycle -Action 'spawn' -LifecycleSummary $Summary -Inputs $startInputs -StatusWord 'START' -ReasonCode 'SUBAGENT_SPAWN' -UseDryRun:$DryRun

if (-not $commandIsAvailable) {
    $blockedSummary = "$Summary (blocked: no sessions_spawn command available; provide -SpawnCommand explicitly)"
    Invoke-OragornLifecycle -Action 'spawn-fail' -LifecycleSummary $blockedSummary -Inputs $startInputs -StatusWord 'BLOCKED' -ReasonCode 'BLOCKED_NO_SPAWN_COMMAND' -UseDryRun:$DryRun
    Write-Error 'BLOCKED: no sessions_spawn command on PATH and no -SpawnCommand override supplied.'
    exit 42
}

if ($DryRun) {
    Write-Host "[DryRun] spawn command: $commandDisplay"
    Invoke-OragornLifecycle -Action 'spawn-finish' -LifecycleSummary "$Summary (dry-run only)" -Inputs $startInputs -Outputs @("spawn_cmd:$commandDisplay") -StatusWord 'INFO' -ReasonCode 'DRY_RUN_NO_EXECUTION' -UseDryRun
    exit 0
}

$spawnExitCode = 0
try {
    $cmd = $resolvedCommand[0]
    $cmdArgs = @()
    if ($resolvedCommand.Count -gt 1) {
        $cmdArgs = $resolvedCommand[1..($resolvedCommand.Count - 1)]
    }

    & $cmd @cmdArgs
    $spawnExitCode = $LASTEXITCODE
}
catch {
    $spawnExitCode = 1
    Write-Error "Spawn command failed to execute: $($_.Exception.Message)"
}

if ($spawnExitCode -eq 0) {
    Invoke-OragornLifecycle -Action 'spawn-finish' -LifecycleSummary "$Summary (spawn command completed)" -Inputs $startInputs -Outputs @("spawn_cmd:$commandDisplay", "exit_code:$spawnExitCode") -StatusWord 'OK' -ReasonCode 'SUBAGENT_FINISH'
    exit 0
}

Invoke-OragornLifecycle -Action 'spawn-fail' -LifecycleSummary "$Summary (spawn command failed)" -Inputs $startInputs -Outputs @("spawn_cmd:$commandDisplay", "exit_code:$spawnExitCode") -StatusWord 'FAIL' -ReasonCode 'SUBAGENT_FAIL'
exit $spawnExitCode
