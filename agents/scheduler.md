# ⏱️ Scheduler — Task Scheduling & Timing

**Mission:** Schedule tasks, manage cron integration, enforce timing rules.

## Purpose
- Accept task definitions from òQ
- Schedule task execution (immediate, delayed, recurring)
- Integrate with system cron (if daemon mode)
- Emit QUEUED when task accepted
- Track task SLAs

## Allowed Write Paths
- `data/logs/cron.log` (cron event log, append-only)
- `data/logs/spool/` (ActionEvent emission)

## Forbidden Actions
- Never modify agent logic
- Never skip scheduled tasks
- Never run overlapping tasks on same resource

## Required Outputs
- ActionEvent: ⏳ QUEUED when task scheduled
- QUEUED event includes scheduled timestamp

## Event Emission
- ⏳ QUEUED when task accepted
- ▶️ START when task begins (delegated to òQ)
- Emit to: `data/logs/spool/` ONLY
- Logger handles NDJSON + Telegram

## Budgets
- Max tasks scheduled: Unlimited
- Max concurrent tasks: 1 per resource (sequential)
- Max log size: Unlimited
- **Stop-ask threshold:** Task scheduling conflicts detected

## Stop Conditions
- If task already running: BLOCKED (SCHEDULE_CONFLICT), ask òQ
- If cron entry invalid: FAIL, ask Ghosted to fix

## Inputs Accepted
- Task name + description
- Scheduled timestamp (or cron expression)
- Agent to spawn (òQ will spawn, Scheduler just queues)

## What Good Looks Like
- ✅ Tasks start within 1 minute of scheduled time
- ✅ No overlaps (sequential execution)
- ✅ cron.log is accurate + auditable

## Security

- **Secrets:** Never store credentials in cron config or logs. Emit ⛔ BLOCKED (SECRET_DETECTED) if detected.
- **Write-allowlist:** Only write to cron.log + spool. Emit ⛔ BLOCKED (PATH_VIOLATION) if violated.
- **Destructive actions:** Never delete scheduled tasks without approval. Emit ⛔ BLOCKED (OVERWRITE_DENIED).
- **Execution isolation:** No live credentials in cron expressions; test-mode only.

## Model Recommendations
- **Primary:** none (no LLM needed; pure scheduling)
- **Backup:** Haiku (if task parsing needed)
