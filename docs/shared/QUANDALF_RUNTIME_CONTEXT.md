# Quandalf Runtime Context

Last updated: 2026-03-04

## Execution/Handoff Model (Current)

- Frodex emits terminal run events in `data/logs/actions.ndjson` (authoritative completion marker: `LAB_SUMMARY` with `run_id=autopilot-...`).
- `scripts/automation/check_quandalf_handoff.ps1` polls every minute and triggers Quandalf execution exactly once per new completed Frodex run.
- Handoff idempotency state: `data/state/quandalf_handoff_poll_state.json`.
- Handoff lock: `data/state/locks/quandalf_handoff_poll.lockdir`.

## Shared Mutex (No Overlap)

All Quandalf pipeline writers share one lock:
- `data/state/locks/quandalf_pipeline.lockdir`

This lock is used by:
- `scripts/quandalf-auto-execute.sh`
- `scripts/claude-tasks/run-strategy-researcher.ps1`
- `scripts/claude-tasks/run-strategy-generator.ps1`
- `scripts/claude-tasks/run-doctrine-synthesizer.ps1`
- `scripts/claude-tasks/run-backtest-auditor.ps1`

If the lock is held, task should skip safely and emit WARN (never force overlap writes).

## Logging Contract (Quandalf)

Handoff-triggered Quandalf log card title:
- `🪞 Reflecting`

Activity fields:
- `Reviewed`
- `Advanced`
- `Aborted`
- `Queued`

Note format:
- One natural sentence.
- Do not restate activity lines verbatim.

## Operational Principle

- Prefer soft warnings over hard blocks for strategy count/shape quality.
- Keep pipeline moving; surface quality guidance in logs instead of stopping execution.
