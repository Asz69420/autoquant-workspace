# SOUL.md (On-Demand Reference)

Persona baseline is now `SOUL-DIGEST.md`.
Full evolving persona guidance moved to `SOUL-FULL.md`.
Load this file only for deep persona/boundary review.

## Pre-Commit Gate

Before every commit I make or approve, run this gate:

1. **Syntax/parse check all changed files**
   - Python: `python -m py_compile <changed.py>`
   - JSON: `python -m json.tool <changed.json> > $null`
   - PowerShell: `powershell -NoProfile -Command "[void][System.Management.Automation.Language.Parser]::ParseFile('<changed.ps1>', [ref]$null, [ref]$null)"`
2. **Dry run or validation where possible**
   - Prefer `--dry-run`, `--check`, or validator commands for touched components.
3. **If pipeline scripts were touched, run a safe test**
   - Use a bounded/safe invocation (example: `scripts\pipeline\autopilot_worker.ps1 -DryRun`).
4. **If config was touched, verify gateway still starts**
   - Run `openclaw status` and confirm config validation passes and gateway is reachable.

If any gate fails, do not commit until fixed.

## Emergency Procedures

Fallback moves when something goes wrong:

1. **Revert local tracked edits**
   - `git checkout -- .`
2. **Restart gateway**
   - `openclaw gateway restart`
3. **Stop autopilot**
   - Stop current task run: `schtasks /End /TN "\AutoQuant-autopilot"`
   - Disable future runs: `schtasks /Change /TN "\AutoQuant-autopilot" /Disable`
4. **Kill a stuck task**
   - Find related process: `Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'autopilot_worker\.ps1|run_autopilot_task\.ps1' } | select ProcessId,Name,CommandLine`
   - Kill by PID: `Stop-Process -Id <PID> -Force`
   - If no autopilot process remains and lock persists, remove stale lock: `Remove-Item data\state\locks\autopilot_worker.lock -Force`
