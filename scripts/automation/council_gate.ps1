param(
  [switch]$ExplicitUserRequest
)

$ErrorActionPreference = 'Stop'

if (-not $ExplicitUserRequest) {
  Write-Output 'BLOCKED_UNAUTHORIZED_COUNCIL'
  exit 43
}

Write-Output 'ALLOW_COUNCIL'
exit 0
