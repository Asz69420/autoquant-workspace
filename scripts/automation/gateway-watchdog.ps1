$procs = Get-CimInstance Win32_Process -Filter "Name='openclaw.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'gateway' }

if ($procs) { exit 0 }

Start-Process -FilePath "openclaw" -ArgumentList "gateway" -WindowStyle Hidden

$runId = "watchdog-gateway-$(Get-Date -Format 'yyyyMMddHHmmss')"
$summary = "Gateway watchdog restarted OpenClaw gateway process."

python scripts/log_event.py `
  --run-id $runId `
  --agent "System" `
  --model-id "system/watchdog" `
  --action "GATEWAY_RESTART" `
  --status-word "OK" `
  --status-emoji "✅" `
  --reason-code "GATEWAY_RESTART" `
  --summary $summary
