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
$frodexBundleTask = '\frodex-bundle-log-15m'

if ($Enabled) {
  schtasks /Change /TN $frodexTask /Disable | Out-Null
  # Hyper chain trigger (completed run -> Quandalf -> trigger next Frodex)
  schtasks /Change /TN $handoffTask /Enable | Out-Null
  # Prevent duplicate Frodex cards in hyper mode (run_autopilot_task emits event-driven card already).
  schtasks /Change /TN $frodexBundleTask /Disable | Out-Null
  Write-Host 'Hyper mode ENABLED: frodex 15m disabled; handoff poller enabled; frodex bundle-log schedule disabled.'
} else {
  schtasks /Change /TN $frodexTask /Enable | Out-Null
  schtasks /Change /TN $handoffTask /Enable | Out-Null
  schtasks /Change /TN $frodexBundleTask /Enable | Out-Null
  Write-Host 'Hyper mode DISABLED: enabled frodex 15m schedule + handoff poller + frodex bundle-log schedule.'
}

Write-Host ('runtime_flags.hyperMode=' + ([string]([bool]$Enabled)).ToLowerInvariant())
