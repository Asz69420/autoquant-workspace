# Oragorn Context Sync (Daily)

## Purpose
Keep Oragorn's context documents fresh from deterministic system state.

Updated files:
- `agents/oragorn/agent/CONTEXT.md`
- `docs/claude-context/SESSION_CONTEXT.md`

## Scripts
- Updater: `scripts/automation/update_oragorn_context.py`
- Runner: `scripts/automation/run-oragorn-context-sync.ps1`
- Task setup: `scripts/automation/setup_oragorn_context_sync_task.ps1`

## Schedule
- Windows Task Scheduler task: `AutoQuant-Oragorn-ContextSync`
- Frequency: daily at **03:00**

## Manual run
```powershell
powershell -ExecutionPolicy Bypass -File scripts/automation/run-oragorn-context-sync.ps1
```

## What is refreshed
- `## Live Pipeline Snapshot (auto-updated)`
- `## Known Issues (auto-updated)`
- `## Roadmap Progress (auto-updated)`

## Logging
The updater emits ActionEvents via `scripts/log_event.py` with:
- `agent=Oragorn`
- `action=CONTEXT_REFRESH`
- `reason_code=CONTEXT_REFRESHED|NOOP_CONTEXT_CURRENT|...`
