# Focus Loop Cron Runbook

Purpose: run long tasks in repeat intervals without manual check-ins.

## What it does
- Creates a cron job (`focus-<name>`) that pings an isolated agent session on a fixed interval.
- Agent continues work until one of two terminal states:
  - `FOCUS_DONE: ...`
  - `FOCUS_BLOCKED: ...`

## Commands
From repo root:

```powershell
# Start (default 15m)
.\scripts\automation\focus_loop.ps1 start --name tv-parity --task "continue TradingView parity harness"

# Start with custom interval
.\scripts\automation\focus_loop.ps1 start --name strat-a --every 30m --task "iterate Strategy A robustness tests"

# List active focus loops
.\scripts\automation\focus_loop.ps1 list

# Stop a focus loop
.\scripts\automation\focus_loop.ps1 stop --name tv-parity

# Sweep all focus loops and auto-stop finished/blocked ones
.\scripts\automation\focus_loop.ps1 sweep
```

## Scheduling guidance
- Use `10m` to `30m` for active build tasks.
- Use `1h`+ for slower research or monitoring loops.
- Avoid overlapping loops on the same task area.

## Reliability
- Uses OpenClaw cron + isolated sessions.
- Survives restarts as long as gateway scheduler is running.

## Auto-stop behavior
- Terminal markers are detected from latest run summary (`openclaw cron runs --id <jobId> --limit 1`).
- If latest summary includes either marker below, `sweep` disables and removes that loop:
  - `FOCUS_DONE:`
  - `FOCUS_BLOCKED:`
- Safe/idempotent: loops with no runs or no terminal marker are left unchanged.

## Recommended scheduler hook
- Run sweep on a periodic schedule (for example every 10-15 minutes) so completed/blocked loops self-clean quickly.
- Manual one-liner:
  - `.\scripts\automation\focus_loop.ps1 sweep`

## Notes
- Keep prompts narrow and outcome-driven.
- Prefer one loop per objective.
- If blocked, resolve dependency then restart or continue same loop.
