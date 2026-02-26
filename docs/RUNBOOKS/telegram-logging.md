# Runbook: Telegram Logging & Alerting

## Architecture (Single-Sender Model)

Only **one component (🧾 Logger)** is allowed to send messages to Telegram.

```
Agent 1 ─┐
Agent 2 ─┼─ emit ActionEvents → outbox files → Telegram Reporter ─── Telegram (Log Group)
Agent N ─┘                      (data/logs/outbox/)      (formatted messages)
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

## ActionEvent Outbox (Event Transport)

**Path:** `data/logs/outbox/{ts_file}___{run_id}___{agent}___{status_word}.json`

**Timestamp format in filename:** `YYYYMMDDTHHMMSSZ` (no colons; Windows-safe)

**Example filename:** `20260222T150100Z___backtest--a1b2c3d4e5f6___BacktestRunner___OK.json`

(Note: `ts_iso` inside the JSON body uses standard ISO 8601 with colons)

**Write process (all agents):**
1. Create ActionEvent JSON with `ts_iso` (ISO 8601) and `ts_local` (Brisbane AEST)
2. Extract filename-safe timestamp: `20260222T150100Z`
3. Write to outbox atomically: `data/logs/outbox/{ts_file}___{run_id}___{agent}___{status_word}.json`
4. Outbox file = temporary; Telegram Reporter will delete after processing

**Telegram Reporter drain process:**
1. Scan outbox/ in timestamp order (by filename); also check legacy spool/ for backward compatibility
2. For each file: parse → format Telegram message → send → append to NDJSON → delete outbox/spool file
3. If Telegram send fails: write FAIL ActionEvent to errors.ndjson, keep file in queue, retry next cycle
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

## Outbox Troubleshooting

**Q: Outbox file stuck for hours?**
- Telegram Reporter may have crashed or lost connection to Telegram
- Check `errors.ndjson` for failed send attempts
- Manually drain: `python scripts/tg_reporter.py --manual`

**Q: How do I clear stale outbox files?**
```bash
# List outbox files older than 24h
find data/logs/outbox/ -mtime +1 -type f

# Archive or delete (carefully!)
# It's safe to delete if you don't care about the action
```

**Q: Telegram message didn't arrive but outbox file was deleted?**
- Telegram Reporter sent successfully to Telegram API, but message didn't render on client
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

## Leaderboard

- Official output: `artifacts/reports/leaderboard.txt`
- Generator: `scripts/pipeline/write_leaderboard_txt.py`
- Telegram command: `leaderboard` (regenerates and sends the file as a document attachment)

## Scheduling

- `\AutoQuant-autopilot` — **Lab (research loop)**: every hour on the hour (`00:00, 01:00, ... 23:00`)
- `\AutoQuant-youtube-watch` — **Harvester (ingestion loop)**: twice per day at `08:10` and `20:10` (AEST)
- `\AutoQuant-tv-catalog` — **Harvester (ingestion loop)**: once per day at `09:00` (AEST)
- `\AutoQuant-keeper-30m` — unchanged (`:00` / `:30`)
- `\AutoQuant-tg_reporter` — daemon cadence unchanged

Collision rules:
- Single-instance/no-overlap (`MultipleInstances=IgnoreNew`)
- Unattended S4U execution with highest privileges retained
- Working directory and action command unchanged unless explicitly approved

## Running tg_reporter (Daemon vs Manual)

### When to Use Daemon

**Use daemon during active work sessions:**
- Spawn sub-agents that emit events
- Backtesting running in parallel
- Real-time Telegram alerts are helpful
- You want live logs of progress

**Command:**
```powershell
# Terminal 1: Start daemon (checks queue every 15s)
python scripts\tg_reporter.py --daemon --interval 15
```

Stop anytime: `Ctrl+C`

### When to Use Manual Drain

**Use manual drain when:**
- Work session is over; want a final summary
- You prefer quiet/batch logging
- Debugging a specific event
- Running in CI/cron (not 24/7)

**Command:**
```powershell
# One-time drain and exit
python scripts\tg_reporter.py --manual
```

### Important: tg_reporter is Always-On (Non-Negotiable)

Telegram Reporter must run continuously with self-healing automation.
All other agents (Backtester, Reader, Strategist, etc.) are spawned on-demand per work packet.

Required controls:
- `AutoQuant-tg_reporter` scheduled task with startup + repeating trigger
- restart-on-failure policy enabled
- `AutoQuant-tg_reporter-watchdog` scheduled task to restart on missing/stuck state

### Health Check Commands

```powershell
# See current queue depth
ls data\logs\outbox

# View last 5 events sent
Get-Content data\logs\actions.ndjson -Tail 5

# Check for errors (failed sends)
Get-Content data\logs\errors.ndjson -Tail 10

# Watch daemon in real-time (optional)
Get-Content data\logs\actions.ndjson -Tail 1 -Wait
```

### Anti-Spam Limits

Telegram Reporter enforces:
- **Max 20 Telegram messages per drain cycle** → sends rollup INFO if queue exceeds
- **60-second dedup window** → same (run_id, status_word) pair sent once per 60s
- **Max 5 consecutive failures** → daemon exits; manual check required

**Example:** If 30 events in queue and max is 20, first 20 are sent, then:
```
ℹ️ INFO: "10 more events queued"
Run: logger-rollup
```

This prevents log floods while ensuring nothing is permanently lost.

### Windows Tasking (Required)

Use scheduled tasks, not manual terminals:
- `AutoQuant-tg_reporter` (daemon)
- `AutoQuant-tg_reporter-watchdog` (health + restart)

Setup/repair command:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/ensure_tg_reporter_watchdog.ps1
```

Healthcheck command (fail-closed):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/check_logger_health.ps1
```

---

**See also:** `schemas/ActionEvent.md`, `scripts/log_event.py`, `scripts/tg_notify.py`, `scripts/tg_reporter.py`
