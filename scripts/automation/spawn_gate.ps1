param(
  [Parameter(Mandatory = $true)][string]$Channel,
  [Parameter(Mandatory = $true)][string]$ChatType,
  [switch]$ExplicitUserOverride
)

$ErrorActionPreference = 'Stop'

# Hard rule:
# In direct chats, sessions_spawn is blocked unless user explicitly requested in-DM spawn.
if ($ChatType -eq 'direct' -and -not $ExplicitUserOverride) {
  Write-Output 'BLOCKED_DM_SPAWN'
  exit 42
}

Write-Output 'ALLOW_SPAWN'
exit 0
