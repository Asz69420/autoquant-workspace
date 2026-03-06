$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\Clamps\.openclaw\workspace'

$gatewayHost = '127.0.0.1'
$gatewayPort = 18789
$probeTimeoutMs = 3000

function Test-GatewayHealthy {
  param([string]$ProbeHost, [int]$ProbePort, [int]$TimeoutMs)

  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $ar = $client.BeginConnect($ProbeHost, $ProbePort, $null, $null)
    $ok = $ar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if (-not $ok) { return $false }
    $client.EndConnect($ar)
    return $true
  } catch {
    return $false
  } finally {
    try { $client.Close() } catch {}
  }
}

function Start-Gateway {
  $p = Start-Process -FilePath 'openclaw.cmd' -ArgumentList @('gateway','start') -PassThru -WindowStyle Hidden -Wait
  return [int]$p.ExitCode
}

function Emit-Event {
  param(
    [string]$Action,
    [string]$StatusWord,
    [string]$StatusEmoji,
    [string]$ReasonCode,
    [string]$Summary
  )

  $runId = "watchdog-gateway-$(Get-Date -Format 'yyyyMMddHHmmss')"

  python scripts/log_event.py `
    --run-id $runId `
    --agent "System" `
    --model-id "system/watchdog" `
    --action $Action `
    --status-word $StatusWord `
    --status-emoji $StatusEmoji `
    --reason-code $ReasonCode `
    --summary $Summary | Out-Null
}

# 1) Health check first: no action if healthy.
if (Test-GatewayHealthy -ProbeHost $gatewayHost -ProbePort $gatewayPort -TimeoutMs $probeTimeoutMs) {
  Write-Host 'Gateway healthy; no action.'
  exit 0
}

# 2) Down -> start only (never stop/restart).
$startExit = Start-Gateway
Start-Sleep -Seconds 3

# 3) Verify recovery.
if (Test-GatewayHealthy -ProbeHost $gatewayHost -ProbePort $gatewayPort -TimeoutMs $probeTimeoutMs) {
  Emit-Event -Action 'GATEWAY_START' -StatusWord 'OK' -StatusEmoji '✅' -ReasonCode 'GATEWAY_START' -Summary 'Gateway watchdog started OpenClaw gateway after failed health probe.'
  Write-Host 'Gateway started by watchdog.'
  exit 0
}

Emit-Event -Action 'GATEWAY_START_FAIL' -StatusWord 'WARN' -StatusEmoji '⚠️' -ReasonCode 'GATEWAY_START_FAIL' -Summary ('Gateway watchdog attempted start but probe still failed (start_exit=' + $startExit + ').')
Write-Host ('Gateway start attempt failed. ExitCode=' + $startExit)
exit 1
