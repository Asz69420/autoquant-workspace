$ErrorActionPreference = 'Stop'

Write-Output 'SMOKE A: enqueue 3 build requests'
$outs = @()
$outs += powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'build smoke queue one' -UpdateId ('smoke-a1-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outs += powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'build smoke queue two' -UpdateId ('smoke-a2-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outs += powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'build smoke queue three' -UpdateId ('smoke-a3-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outs | ForEach-Object { Write-Output $_ }

Write-Output 'SMOKE B: FAST_PATH while queued'
$outB = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'turn warnings off' -UpdateId ('smoke-b-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outB | ForEach-Object { Write-Output $_ }

Write-Output 'SMOKE C: queue controls'
$outC1 = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'queue status' -UpdateId ('smoke-c1-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outC2 = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'cancel next' -UpdateId ('smoke-c2-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outC3 = powershell -ExecutionPolicy Bypass -File scripts/automation/route_request.ps1 -Message 'clear queue' -UpdateId ('smoke-c3-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) 2>&1
$outC1 | ForEach-Object { Write-Output $_ }
$outC2 | ForEach-Object { Write-Output $_ }
$outC3 | ForEach-Object { Write-Output $_ }

Write-Output 'SMOKE D: stale lock fail-closed'
$lockPath = 'data/state/build_queue.lock'
$stale = @{ pid = '99999'; started_at = ([DateTimeOffset]::UtcNow.AddMinutes(-10).ToString('o')); heartbeat = ([DateTimeOffset]::UtcNow.AddMinutes(-10).ToString('o')) }
$dir = Split-Path -Parent $lockPath
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
Set-Content -Path $lockPath -Value ($stale | ConvertTo-Json -Depth 5) -Encoding utf8
$old = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$workerOut = powershell -ExecutionPolicy Bypass -File scripts/automation/build_queue_worker.ps1 2>&1
$ErrorActionPreference = $old
$workerOut | ForEach-Object { Write-Output $_ }

Write-Output 'SMOKE done'
