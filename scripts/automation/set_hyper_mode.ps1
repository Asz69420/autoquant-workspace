[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [bool]$Enabled
)

$ErrorActionPreference = 'Stop'
$ROOT = 'C:\Users\Clamps\.openclaw\workspace'
Set-Location -LiteralPath $ROOT

$runtimeFlagsPath = Join-Path $ROOT 'config\runtime_flags.json'
if (-not (Test-Path -LiteralPath $runtimeFlagsPath)) {
  '{"warningsEnabled":false,"hyperMode":false}' | Set-Content -LiteralPath $runtimeFlagsPath -Encoding UTF8
}

$flags = Get-Content -LiteralPath $runtimeFlagsPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not ($flags.PSObject.Properties.Name -contains 'warningsEnabled')) {
  $flags | Add-Member -NotePropertyName warningsEnabled -NotePropertyValue $false
}
if ($flags.PSObject.Properties.Name -contains 'hyperMode') {
  $flags.hyperMode = [bool]$Enabled
} else {
  $flags | Add-Member -NotePropertyName hyperMode -NotePropertyValue ([bool]$Enabled)
}
$flags | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $runtimeFlagsPath -Encoding UTF8

$frodexTask = '\frodex-ops-loop-15m'
$handoffTask = '\quandalf-handoff-check-1m'

if ($Enabled) {
  schtasks /Change /TN $frodexTask /Disable | Out-Null
  # Keep 1m handoff poller as watchdog for missed event-delivery recovery.
  schtasks /Change /TN $handoffTask /Enable | Out-Null
  Write-Host 'Hyper mode ENABLED: frodex 15m schedule disabled; handoff poller left enabled as watchdog.'
} else {
  schtasks /Change /TN $frodexTask /Enable | Out-Null
  schtasks /Change /TN $handoffTask /Enable | Out-Null
  Write-Host 'Hyper mode DISABLED: enabled frodex 15m schedule + quandalf handoff poller (normal mode).'
}

Write-Host ('runtime_flags.hyperMode=' + ([string]([bool]$Enabled)).ToLowerInvariant())
