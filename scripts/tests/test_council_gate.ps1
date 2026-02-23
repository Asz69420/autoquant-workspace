$ErrorActionPreference = 'Stop'

# blocked without explicit user request
powershell -ExecutionPolicy Bypass -File scripts/automation/council_gate.ps1 | Out-Null
if ($LASTEXITCODE -ne 43) { throw 'Expected council gate to block without explicit request (43)' }

# allowed with explicit user request
powershell -ExecutionPolicy Bypass -File scripts/automation/council_gate.ps1 -ExplicitUserRequest | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Expected council gate to allow with explicit request (0)' }

Write-Output 'PASS: council gate rules enforced'
