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

$taskName = '\frodex-ops-loop-15m'
if ($Enabled) {
  schtasks /Change /TN $taskName /Disable | Out-Null
  Write-Host 'Hyper mode ENABLED: frodex-ops-loop-15m schedule disabled.'
} else {
  schtasks /Change /TN $taskName /Enable | Out-Null
  Write-Host 'Hyper mode DISABLED: frodex-ops-loop-15m schedule enabled.'
}

Write-Host ('runtime_flags.hyperMode=' + ([string]([bool]$Enabled)).ToLowerInvariant())
