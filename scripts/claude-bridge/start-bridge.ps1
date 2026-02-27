$ROOT = "C:\Users\Clamps\.openclaw\workspace"
$BRIDGE_DIR = "$ROOT\scripts\claude-bridge"

# Load .env
if (Test-Path "$BRIDGE_DIR\.env") {
    Get-Content "$BRIDGE_DIR\.env" | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

Write-Host "Starting Claude CLI Bridge (Quandalf)..." -ForegroundColor Cyan
python "$BRIDGE_DIR\telegram_claude_bridge.py"
