$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $root 'scripts\pipeline\write_daily_intel_txt.py'
python "$script" --send-telegram
