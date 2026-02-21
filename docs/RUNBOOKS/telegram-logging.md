# Runbook: Telegram Logging & Alerting

## Architecture (Single-Sender Model)

Only **one component (Logger)** is allowed to send messages to Telegram.

```
Agent 1 ─┐
Agent 2 ─┼─ emit ActionEvents → spool files → Logger ─── Telegram (Log Group)
Agent N ─┘                     (data/logs/spool/)        (formatted messages)
                                                            + NDJSON logs
                                                            (data/logs/actions.ndjson)
```

**Why:**
- Prevents double-logging and log storms
- Centralized formatting and retry logic
- Single point of audit/control

**Routing Separation:**
- **Log group (`TELEGRAM_LOG_CHAT_ID`):** All backtest alerts + ActionEvents
- **Command chat (`TELEGRAM_CMD_CHAT_ID`):** Your DM; for commands + replies only
- **Enforcement:** Logger always sends to log group. (Future) Commander only accepts from DM.

## ActionEvent Spool (Event Transport)

**Path:** `data/logs/spool/{ts_file}___{run_id}___{agent}___{status_word}.json`

**Timestamp format in filename:** `YYYYMMDDTHHMMSSZ` (no colons; Windows-safe)

**Example filename:** `20260222T150100Z___backtest--a1b2c3d4e5f6___BacktestRunner___OK.json`

(Note: `ts_iso` inside the JSON body uses standard ISO 8601 with colons)

**Write process (all agents):**
1. Create ActionEvent JSON with `ts_iso` (ISO 8601) and `ts_local` (Brisbane AEST)
2. Extract filename-safe timestamp: `20260222T150100Z`
3. Write to spool atomically: `data/logs/spool/{ts_file}___{run_id}___{agent}___{status_word}.json`
4. Spool file = temporary; Logger will delete after processing

**Logger drain process:**
1. Scan spool/ in timestamp order (by filename)
2. For each file: parse → format Telegram message → send → append to NDJSON → delete spool file
3. If Telegram send fails: write FAIL ActionEvent to errors.ndjson, keep spool file, retry next cycle
4. Run continuously (daemon) or via cron

## Telegram Message Format (MANDATORY)

**Strict template (code block):**
```
[<timestamp 12h AM/PM AEST>] <AgentName> | <model-id> | <status_emoji> <STATUS_WORD> (<reason_code_if_any>)
<Line 2: summary / what happened (max 50 chars)>
<Line 3: optional detail (max 50 chars)>
Run: <run_id>
```

**Example: Backtest OK**
```
[22 Feb 10:01 AM AEST] BacktestRunner | n/a | ✅ OK
Backtest: strategy-mean-revert-btc-v1, Sharpe 1.2
2024-01-01 to 2024-12-31 (365 days)
Run: backtest--a1b2c3d4e5f6
```

**Example: Backtest FAIL**
```
[22 Feb 10:05 AM AEST] BacktestRunner | n/a | ❌ FAIL (TIMEOUT)
Execution exceeded 600 seconds
Attempted: strategy-example-v2.json
Run: backtest--x9y8z7w6v5u4
```

**Example: Indicator BLOCKED**
```
[22 Feb 10:10 AM AEST] SpecValidator | haiku | ⛔ BLOCKED (NEEDS_APPROVAL)
New indicator spec requires approval
File: indicator-volatility-zscore-v2.json
Run: add-indicator--vol-zscore-v2
```

**Rules:**
- Wrap entire message in triple backticks
- First line (header) is mandatory; format exactly as shown
- Timestamp: Brisbane local time, 12-hour format with AM/PM and AEST
- Lines 2–3: keep tight (max 50 chars each)
- No stack traces in Telegram (errors.ndjson has full details)
- If `reason_code` present, include in parentheses after status word

## Status Emojis & Meanings

| Emoji | Status | Meaning |
|-------|--------|---------|
| ▶️ | START | Started a task |
| ✅ | OK | Completed successfully |
| ⚠️ | WARN | Completed with issues / partial output |
| ❌ | FAIL | Failed (exception/error) |
| ⛔ | BLOCKED | Firewall / needs approval / policy violation |
| ⏭️ | SKIP | Skipped (duplicate / already done / not applicable) |
| ⏸️ | PAUSE | Paused (waiting on user / external dependency) |
| ⏳ | QUEUED | Task accepted and queued |
| 🔁 | RETRY | Retrying (include attempt count: "2/5") |
| 🐢 | THROTTLED | Rate-limited / backing off |
| 🛑 | CANCELLED | Cancelled by user/supervisor |
| 🧊 | ARCHIVED | Moved to cold storage |
| 🧪 | TESTING | Evaluation/backtest in progress |
| 🏆 | PROMOTED | Promoted to higher status |
| 🗑️ | REJECTED | Rejected (include short reason) |
| ℹ️ | INFO | Optional FYI (use sparingly) |

## Reason Codes (Optional)

Use when status is WARN, FAIL, BLOCKED, SKIP, REJECTED.

**Safety / Pipeline:**
- `NEEDS_APPROVAL` — Awaiting manual approval
- `PATH_VIOLATION` — File path outside allowed scope
- `OVERWRITE_DENIED` — Attempted to overwrite existing file
- `SECRET_DETECTED` — Credentials/keys found in spec
- `BUDGET_EXCEEDED` — Compute budget exhausted

**Data / Ingestion:**
- `RIGHTS_UNKNOWN` — Rights/license unclear
- `SOURCE_UNREACHABLE` — External API/URL unavailable
- `TRANSCRIPT_FAIL` — Video/audio transcription failed
- `PARSE_FAIL` — Data parsing error
- `DATA_MISMATCH` — Schema mismatch
- `DUPLICATE_HASH` — Artifact already exists (dedup)

**Research / Spec Quality:**
- `GENERIC_IDEA` — Idea too generic / not novel
- `UNTESTABLE` — Spec cannot be tested
- `NO_FALSIFICATION` — No clear falsification condition
- `LOW_SIGNAL` — Indicator shows weak signal
- `INCOMPLETE_SPEC` — Missing required fields

**Backtest / Eval:**
- `OVERFIT` — Backtest shows overfitting signs
- `FEES_FAIL` — Fee model too aggressive / unrealistic
- `SLIPPAGE_FAIL` — Slippage assumptions too optimistic
- `FRAGILE_PARAMS` — Strategy breaks with small param changes
- `REGIME_FAIL` — Strategy fails in certain market regimes
- `LOW_EDGE` — Edge too small for practical trading
- `LOW_SAMPLE` — Too few trades to draw conclusions
- `HIGH_DD` — Drawdown too high for risk tolerance

**Ops:**
- `RATE_LIMIT` — API rate-limited
- `TIMEOUT` — Operation exceeded time limit
- `DEPENDENCY_DOWN` — External service unavailable
- `DISK_FULL` — Storage exhausted
- `OUT_OF_MEMORY` — Ran out of RAM

## Anti-Spam Logging Rules

**Max per task:**
- 1 QUEUED
- 1 START
- 1 END (OK / WARN / FAIL / BLOCKED / SKIP / PAUSE)

**RETRY:** Only log when attempt number increments (not every retry call).

**THROTTLED:** Max once per backoff cycle (not every loop iteration).

**INFO:** Use sparingly; only for meaningful milestones (not debug logs).

**Example valid sequence:**
```
1. ⏳ QUEUED (task accepted)
2. ▶️ START (task running)
3. 🔁 RETRY (attempt 2/5 - because attempt changed)
4. 🔁 RETRY (attempt 3/5)
5. ✅ OK (completed)
```

## Secrets: Environment Variables Only

**Telegram credentials:**
```bash
export TELEGRAM_BOT_TOKEN="..."  # Set in your shell or .env.local
export TELEGRAM_CHAT_ID="..."    # Never commit!
```

**In code:**
```python
import os
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
# Raise error if missing
if not bot_token or not chat_id:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
# Send to Telegram...
```

**Rules:**
- No tokens in MEMORY.md, specs, or Git-tracked files
- Use `.env.local` or system env vars
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` are in .gitignore
- Use only in `tg_notify.py`

## Timestamp Rules

- **`ts_iso` (in JSON body):** UTC, ISO 8601 format with colons: `"2026-02-22T15:01:00Z"`
- **`ts_local` (in JSON body):** Brisbane local time, 12-hour AM/PM with AEST: `"22 Feb 10:01 AM AEST"`
- **Spool filename `ts_file`:** Filename-safe version of UTC, no colons: `20260222T150100Z`
- **Telegram header:** Brisbane local time, 12-hour AM/PM with AEST: `[22 Feb 10:01 AM AEST]`

**Note:** Australia/Brisbane uses AEST year-round (no daylight saving time).

## Spool Troubleshooting

**Q: Spool file stuck for hours?**
- Logger may have crashed or lost connection to Telegram
- Check `errors.ndjson` for failed send attempts
- Manually drain: `python scripts/logger_drain.py --manual --spool-dir data/logs/spool/`

**Q: How do I clear stale spool files?**
```bash
# List spool files older than 24h
find data/logs/spool/ -mtime +1 -type f

# Archive or delete (carefully!)
# It's safe to delete if you don't care about the action
```

**Q: Telegram message didn't arrive but spool file was deleted?**
- Logger sent successfully to Telegram API, but message didn't render on client
- Check Telegram directly; the message may be there
- Full event is in `actions.ndjson`

## Logging Files

**`data/logs/actions.ndjson`**
- Append-only; one JSON per line
- Every ActionEvent (START, OK, FAIL, RETRY, etc.)
- Use for auditing, querying, long-term history

**`data/logs/errors.ndjson`**
- Only FAIL ActionEvents (+ error details)
- Stack traces, full error messages, context
- Use for debugging failed tasks

**`data/logs/spool/`**
- Temporary; deleted after Logger processes
- If files pile up, Logger may be stuck

---

**See also:** `schemas/ActionEvent.md`, `scripts/log_event.py`, `scripts/tg_notify.py`, `scripts/logger_drain.py`
