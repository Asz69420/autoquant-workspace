# Handoffs — Curated Checkpoints for New Chat Sessions

## Purpose

When transitioning between chat sessions, handoffs provide a **curated, pointer-based checkpoint** so the next session can resume instantly without context explosion.

OpenClaw's native hooks (session memory, command logs) remain enabled and are authoritative. Handoffs are supplements—not replacements—that highlight key decisions, status, and next steps.

Note: Startup behavior is canonical in `USER.md` ("Session Resume Contract (Canonical)"); handoffs are checkpoint supplements only.

## When to Use

- End of active work session (before switching contexts)
- Handing off to a different team member or timeframe
- Before long breaks (to freeze progress)
- Explicit `handoff` or `reset handoff` commands in chat

## Handoff File Structure

**Path:** `docs/HANDOFFS/handoff-YYYYMMDD-HHMM.md`

**Template (≤60 lines, pointer-based):**

```markdown
# Handoff — YYYY-MM-DD HH:MM AEST

## Status (1–3 bullets)
- Current phase / milestone
- What's active right now
- Any blockers

## What's running now (0–2 bullets)
- Daemon status (e.g., tg_reporter running)
- Sub-agents in progress (if any)

## Next 3 tasks (numbered, concrete)
1. Task 1 (e.g., "Test Reader agent on 3 research links")
2. Task 2 (e.g., "Review backtest results in data/artifacts/...")
3. Task 3 (e.g., "Update MEMORY.md with findings")

## Authoritative pointers (exact paths, in this order)
1. USER.md — Operating rules, models, delegation policy
2. Latest handoff file (this file) — Checkpoint
3. MEMORY.md — Long-term memory (curated)
4. agents/index.md — Agent roster + assignments
5. docs/RUNBOOKS/telegram-logging.md — Logger status
6. docs/RUNBOOKS/delegation-policy.md — Current decisions

## Recent decisions (1–5 bullets)
- Decision A: why, when made, link to commit if applicable
- Decision B: outcome, next steps
- etc.

## Notes / blockers (optional)
- Anything not covered above
- Known issues or risks

## Raw history pointers (one line)
- Session logs: OpenClaw command log + data/logs/actions.ndjson (append-only)
```

## Example Handoff

```markdown
# Handoff — 2026-02-22 12:22 AEST

## Status
- Phase 1: Logger + tg_reporter live and tested
- All agents defined in roster; Reader is next build target
- tg_reporter daemon running (PID 4844)

## What's running now
- tg_reporter daemon (interval 15s, checking outbox)

## Next 3 tasks
1. Build 🔗 Reader agent (start with log_event.py + tg_reporter integration test)
2. Test MiniMax M2.5 model integration (config pending)
3. Review backtest framework options (Binance proxy vs Hyperliquid)

## Authoritative pointers
1. USER.md — Haiku primary, Codex fallback; handoff + notable action logging enabled
2. docs/HANDOFFS/handoff-2026-02-22-1222.md — This checkpoint
3. MEMORY.md — AutoQuant mission + architecture + conventions
4. agents/index.md — 1 built (Logger), 6 planned, 1 future
5. docs/RUNBOOKS/telegram-logging.md — Daemon best practice (15s interval)
6. docs/RUNBOOKS/delegation-policy.md — Assumption: daemon running during work

## Recent decisions
- Switched all agents to Haiku primary, Codex fallback (simplified model strategy)
- Compact Telegram format (emoji, agent, model; no timestamp)
- Notable action logging required for òQ commits/config changes (feeds log group)
- Added handoff protocol for smooth session transitions

## Notes / blockers
- MiniMax M2.5 model ID needs clarification (not accessible yet)
- Backtest framework decision pending (Binance vs Hyperliquid)

## Raw history pointers
- OpenClaw command log + data/logs/actions.ndjson (append-only audit trail)
```
