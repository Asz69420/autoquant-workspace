[CmdletBinding()]
param(
  [string]$question,
  [int]$rounds = 5,
  [string]$name,
  [ValidateSet('adaptive','low','medium','high')]
  [string]$reasoning = 'adaptive',
  [ValidateSet('short','medium')]
  [string]$verbosity = 'short',
  [int]$timeoutSec = 60,
  [switch]$explicitUserRequest,
  [switch]$help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-Usage {
@"
Council mode

This script is intentionally disabled for direct execution.
Direct API-key council path has been removed.
Use OpenClaw-native council routing only.

Guard:
- Council is blocked unless explicitly user-requested.
- Pass: --explicit-user-request
"@
}

if ($help) { Show-Usage; exit 0 }

if ($explicitUserRequest) {
  powershell -ExecutionPolicy Bypass -File scripts/automation/council_gate.ps1 -ExplicitUserRequest | Out-Null
} else {
  powershell -ExecutionPolicy Bypass -File scripts/automation/council_gate.ps1 | Out-Null
}
if ($LASTEXITCODE -ne 0) { throw 'BLOCKED_UNAUTHORIZED_COUNCIL: explicit user request required to run council.' }

throw 'DIRECT_API_PATH_REMOVED: council.ps1 no longer executes council logic directly. Use OpenClaw-native council routing only.'
