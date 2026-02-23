$ErrorActionPreference = 'Stop'

# 1) direct chat without override => blocked
powershell -ExecutionPolicy Bypass -File scripts/automation/spawn_gate.ps1 -Channel telegram -ChatType direct | Out-Null
if ($LASTEXITCODE -ne 42) { throw 'Expected direct/no-override to block (42)' }

# 2) direct chat with override => allow
powershell -ExecutionPolicy Bypass -File scripts/automation/spawn_gate.ps1 -Channel telegram -ChatType direct -ExplicitUserOverride | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Expected direct/override to allow (0)' }

# 3) non-direct chat => allow
powershell -ExecutionPolicy Bypass -File scripts/automation/spawn_gate.ps1 -Channel telegram -ChatType group | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Expected group to allow (0)' }

Write-Output 'PASS: spawn gate rules enforced'
