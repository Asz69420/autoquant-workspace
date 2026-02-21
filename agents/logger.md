# 🧾 Logger — Telegram Drain & Logging (ONLY SENDER)

**Mission:** **ONLY** Telegram + NDJSON sender; drain spool, format, retry, log everything deterministically.

## Purpose
- Drain `data/logs/spool/` in timestamp order (deterministic)
- Format ActionEvent → Telegram code-block message
- Send to Telegram via env vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Append all ActionEvents to `data/logs/actions.ndjson` (append-only, all events)
- Append FAIL events + error details to `data/logs/errors.ndjson` (append-only, runtime errors only; BLOCKED excluded)
- Implement retry logic (keep spool file on send failure)

## Allowed Write Paths
- **ONLY:** `data/logs/actions.ndjson` (append-only, all events)
- **ONLY:** `data/logs/errors.ndjson` (append-only, FAIL events + error details only)
- **ONLY:** Telegram messages (via env vars)
- Read-only: `data/logs/spool/` (parse, then delete on success)

**NO OTHER WRITES** — Logger is a pure drain + formatter.

## Forbidden Actions
- Never modify spool files (only read → delete on success)
- Never write to artifacts, specs, or Git-tracked files
- Never send secrets in Telegram messages
- Never hardcode Telegram credentials (env vars only)
- Never modify other agents' output
- Never append BLOCKED events to errors.ndjson (they're policy gating, not runtime errors)

## Required Outputs
- Telegram messages (formatted code blocks, max 20 per drain cycle)
- ActionEvent appended to `data/logs/actions.ndjson` (all events)
- FAIL events + error details appended to `data/logs/errors.ndjson` (runtime errors only)
- Spool file deleted after successful send (or kept if send fails)

## Event Emission
- ▶️ START when drain cycle begins
- ✅ OK when spool drained (N events sent, M failed, logged to NDJSON)
- ℹ️ INFO (optional) if >20 messages queued (roll-up: "N more events in logs")
- ❌ FAIL per-event if Telegram send fails 5x consecutive (keep spool, log FAIL to errors.ndjson)
- Emit self-events to: `data/logs/spool/` (Logger logs itself)

## Budgets (Per Drain Cycle)
- Max files created: 0 (read spool, don't create new files)
- Max MB written: 10 MB per drain cycle (NDJSON is append-only)
- Max Telegram messages sent: 20 (roll-up as INFO if more queued)
- Max specs touched: 0 (Logger doesn't create specs)
- **Stop-ask threshold:** Telegram send fails 5x in a row OR no env vars on startup

## Stop Conditions
- If TELEGRAM_BOT_TOKEN missing on startup: FAIL and exit
- If TELEGRAM_CHAT_ID missing on startup: FAIL and exit
- If disk full: FAIL, keep spool files
- If Telegram API unreachable 5x: FAIL, keep spool, log FAIL to errors.ndjson, ask Ghosted
- If spool files accumulate >1 hour old: WARN in MEMORY.md (sign of stuck Logger)

## Inputs Accepted
- ActionEvent JSON files from `data/logs/spool/` (all agents emit here)
- Telegram credentials from env vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Timestamp for message header (extract from ActionEvent ts_local, Brisbane AEST)

## What Good Looks Like
- ✅ Spool drained every 60s (daemon mode) or on-demand; zero backlog
- ✅ Telegram messages arrive with correct format (code block, emoji, timestamp AEST, reason code)
- ✅ NDJSON logs clean, queryable, append-only (no overwrites, ever)
- ✅ Retry keeps spool file if send fails (visible in errors.ndjson for audit)
- ✅ Deterministic (same input spool = same NDJSON + Telegram output)

## Security

- **Secrets:** Never log tokens/keys in NDJSON or Telegram. If detected → scan and redact before appending. Emit warning to errors.ndjson.
- **Write-allowlist:** Only write to allowed paths (actions.ndjson, errors.ndjson, Telegram, spool drain). Emit ⛔ BLOCKED (PATH_VIOLATION) if violated.
- **Destructive actions:** Never delete NDJSON logs or spool files (except successful spool → delete after append). Keep audit trail.
- **Execution isolation:** Never store or relay execution credentials in NDJSON or Telegram messages.

## Model Recommendations
- **Primary:** none (no LLM; pure orchestration + formatting per strict template)
- **Backup:** none (don't use LLM unless explicitly requested by Ghosted for debugging)

---

**Logger is the single source of truth for what happened. Every ActionEvent is logged immutably.**
