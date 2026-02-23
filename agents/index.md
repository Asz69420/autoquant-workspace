# AutoQuant Agent Framework

**Objective:** Durable, bloat-free multi-agent pipeline for trading R&D.

## Fixed Agent Roster

| # | Emoji | Name | Mission |
|---|-------|------|---------|
| 1 | 🤖 | òQ | Main orchestrator; enforce USER.md rules; delegate work |
| 2 | ⏱️ | Scheduler | Schedule tasks, manage timing, cron integration |
| 3 | 🛡️ | Firewall | Validate specs, enforce security, block unsafe actions |
| 4 | 🧾 | Logger | **ONLY** Telegram & NDJSON sender; drain outbox, format, retry |
| 5 | 🔗 | Reader | Fetch links/videos, extract content, emit ResearchCards |
| 6 | 🧲 | Grabber | Harvest TradingView indicators, emit IndicatorRecords |
| 7 | 🧠 | Analyser | Generate non-generic trading theses from source material |
| 8 | 📊 | Strategist | Convert theses into StrategySpecs and prioritize tests |
| 9 | 📈 | Backtester | Run backtests, generate BacktestReports, measure |
| 10 | 🗃️ | Keeper | Index artifacts, deduplicate, curate memory, promote strategies |
| 11 | 🔰 | Verifier | Independent build QC: policy, compatibility, and future-proof checks |
| 12 | 🎭 | Specter | Browser-AI bridge (mock-only Build 1); schema validation + safe contract responses |

## Single-Sender Logging Rule (MANDATORY)

**🧾 Logger is the ONLY agent allowed to:**
- Write `data/logs/actions.ndjson` (all ActionEvents: OK, WARN, FAIL, BLOCKED, etc.)
- Write `data/logs/errors.ndjson` (FAIL events + error details only; BLOCKED excluded)
- Send messages to Telegram

**All other agents (including 🛡️ Firewall, 🤖 òQ, etc.):**
- Emit ActionEvents to `data/logs/outbox/` ONLY
- Never write directly to NDJSON files
- Never send to Telegram
- Let Logger handle delivery

Logger drains outbox in timestamp order: parse → format → send Telegram → append to actions.ndjson (+ errors.ndjson if FAIL) → delete outbox file
- Retry logic: if send fails, keep outbox file, log FAIL to errors.ndjson, continue

**Event routing:**
- **actions.ndjson:** ALL events (START, OK, WARN, FAIL, BLOCKED, SKIP, etc.) — complete audit trail
- **errors.ndjson:** FAIL events + error details only — runtime problems (excludes BLOCKED, which is policy gating)

## Pipeline: Happy Path

```
┌─ Reader (Link/Video Ingestion) ─────┐
│ URL (paper, article, video)          │
│ ↓                                    │
│ Fetch + Extract + Optional Transcode │
│ ↓                                    │
│ ResearchCard (Git: research/)        │
│ Video artifact (artifacts/videos/)   │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Grabber (TradingView Harvesting) ──┐
│ TradingView indicator link           │
│ ↓                                    │
│ Fetch Pine code + metadata           │
│ ↓                                    │
│ IndicatorRecord (Git: indicators/specs/) │
│ Pine artifact (artifacts/indicators/) │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Analyser (Thesis) ─────────────────┐
│ ResearchCard(s) + transcript notes   │
│ ↓                                    │
│ Build falsifiable edge hypotheses    │
│ ↓                                    │
│ Thesis package (artifacts/analysis)  │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Strategist (Design) ───────────────┐
│ Thesis package + IndicatorRecord(s)  │
│ ↓                                    │
│ Convert to strategy spec              │
│ ↓                                    │
│ StrategySpec (Git: strategies/specs/) │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Firewall (Validate) ───────────────┐
│ StrategySpec                         │
│ ↓                                    │
│ Check: entry/exit rules, leverage,   │
│ risk, falsification, secrets, paths  │
│ ↓                                    │
│ OK (pass) or BLOCKED (fail + reason) │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Backtester (Execute) ──────────────┐
│ StrategySpec                         │
│ ↓                                    │
│ Run backtest(s)                      │
│ ↓                                    │
│ BacktestReport (artifacts/backtests/) │
│ Metrics: Sharpe, return, drawdown    │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
┌─ Keeper (Index + Curate) ───────────┐
│ BacktestReport                       │
│ ↓                                    │
│ Index into SQLite (artifacts.db)     │
│ Deduplicate by hash                  │
│ Update MEMORY.md summaries           │
│ (Keeper-only; òQ proposes, asks)    │
│ ↓                                    │
└─────────────────────────────────────┘
                ↓
       Review & Promote/Reject
       (Ghosted or Keeper)
```

## Permissions Matrix (Clarified)

| Agent | Read | Write (Allowed) | Forbidden |
|-------|------|-----------------|-----------|
| 🤖 òQ | All | **None** (propose only) | Modify MEMORY.md, docs/DECISIONS, delete files |
| ⏱️ Scheduler | All | cron.log, outbox/ | Modify agent logic |
| 🛡️ Firewall | specs/, docs/, artifacts | outbox/ ONLY | Write to other paths, skip security checks |
| 🧾 Logger | outbox/, all | **actions.ndjson, errors.ndjson, Telegram** | Modify source files |
| 🔗 Reader | external URLs | research/ (ResearchCards), artifacts/videos/, outbox/ | IndicatorRecords, StrategySpecs, MEMORY, docs |
| 🧲 Grabber | external APIs | indicators/specs/, artifacts/indicators/, outbox/ | other specs, MEMORY, docs |
| 🧠 Analyser | research/, artifacts/, indicators/specs/ | artifacts/analysis/, outbox/ | Write strategies/specs directly, modify MEMORY |
| 📊 Strategist | research/, indicators/specs/, artifacts/analysis/ | indicators/specs/ (custom), strategies/specs/, research/, outbox/ | Delete specs, modify MEMORY |
| 📈 Backtester | strategies/specs/, data/ | data/cache/, artifacts/backtests/, outbox/ | Commit to Git, store credentials |
| 🗃️ Keeper | all artifacts | **artifacts.db, MEMORY.md, ADRs (sole authority)**, outbox/ | Delete without backup, store secrets |
| 🔰 Verifier | USER.md, runbooks, agents, MEMORY.md, diffs | outbox/ (and optional artifacts/analysis/ when explicitly requested) | Implement code/doc mutations for audited build, direct Telegram/NDJSON writes |

## Anti-Bloat Budgets (Per Run, Strict Caps)

| Agent | Max Files | Max MB | Max Specs/Cards | Stop-Ask Threshold |
|-------|-----------|--------|-----------------|-------------------|
| 🤖 òQ | 0 | 0 | 0 (propose only) | Any write request |
| ⏱️ Scheduler | 1 | 0.01 | 0 | Scheduling conflicts |
| 🛡️ Firewall | 0 | 0 | 0 | Any policy violation |
| 🧾 Logger | 0 | 10 | 0 (outbox processing only) | 20 TG msg/cycle OR send fails 5x |
| 🔗 Reader | 3 | 100 | 1–3 ResearchCards per link | Any fetch timeout or rights unclear |
| 🧲 Grabber | 10 | 200 | 10 indicators | Fetch fails 3x OR rights unknown |
| 🧠 Analyser | 5 | 10 | 3 thesis packages | Generic thesis or no falsification criteria |
| 📊 Strategist | 5 | 5 | 3 StrategySpecs | Untestable spec or unresolved thesis gaps |
| 📈 Backtester | 3 | 500 | 0 | Suspected overfitting or timeout |
| 🗃️ Keeper | 20 | 50 | 0 | 3 promotions per run max |
| 🔰 Verifier | 0 | 5 | 0 | Missing required evidence or unresolved critical blocker |

## Memory Authority (Keeper-Only)

**🤖 òQ:**
- May propose diffs/patches to MEMORY.md and ADRs
- Must NOT apply changes without asking
- Must emit ActionEvent (ℹ️ INFO) proposing change, wait for Keeper approval

**🗃️ Keeper:**
- **SOLE authority** to edit MEMORY.md and `docs/DECISIONS/` ADRs
- Applies memory updates after reviewing artifact indexing + milestones
- Enforces size limits (<10 KB MEMORY.md)
- Logs all updates to ActionEvent

---

## Security Hardening (MANDATORY for All Agents)

### Core Security Rules

Every agent MUST enforce:

1. **Secrets Rule:** Never paste, log, or store tokens/keys/wallet seeds in any file or Telegram message.
   - If detected: emit ⛔ BLOCKED (SECRET_DETECTED) and STOP immediately.
   - Credentials must come from env vars or credential store only.

2. **Write Allowlist Rule:** Only write to paths in "Write (Allowed)" column above.
   - Any write outside allowed paths: emit ⛔ BLOCKED (PATH_VIOLATION) and STOP.
   - 🛡️ Firewall enforces this for all agents upstream.

3. **No Destructive Actions Rule:** Never overwrite, delete, or reset files without explicit Ghosted approval.
   - Proposed change: emit ℹ️ INFO (NEEDS_APPROVAL) and wait.
   - On destructive request: emit ⛔ BLOCKED (OVERWRITE_DENIED) and escalate to 🤖 òQ.

4. **Execution Isolation Rule:** No live trading, market access, or real credentials until explicitly enabled.
   - Backtester: test mode only (paper trading, simulated data).
   - Credentials must be env vars or credential store, never in repo/files.
   - If execution credentials detected in spec: emit ⛔ BLOCKED (SECRET_DETECTED).

### 🛡️ Firewall Enforcement (Special Responsibility)

Firewall is the security layer. It MUST:

- Scan all specs for embedded secrets (API keys, wallet seeds, passwords)
- Scan all write requests for PATH_VIOLATION (outside allowed dirs)
- Scan all action requests for OVERWRITE_DENIED (delete/reset/overwrite)
- Scan all backtests for live credentials (must be simulated/paper only)
- Emit ⛔ BLOCKED with precise reason_code + remediation advice

---

## Event Emission Rules (All → Outbox; Only Logger → NDJSON + Telegram)

**Every agent (except Logger) emits ActionEvents to `data/logs/outbox/`:**

Example lifecycle:
```
1. ⏳ QUEUED (task accepted)
2. ▶️ START (execution begins)
3. 🔁 RETRY (if needed; include attempt count)
4. ✅ OK or ⚠️ WARN or ❌ FAIL or ⛔ BLOCKED (end state)
```

**Only 🧾 Logger reads outbox, writes NDJSON, sends Telegram:**
- Drains outbox in timestamp order
- Parses ActionEvent JSON
- Formats → Telegram code-block
- Sends via env vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Appends original event to data/logs/actions.ndjson (all events)
- If FAIL: also appends to data/logs/errors.ndjson (runtime errors only; BLOCKED excluded)
- Deletes outbox file on success; keeps on send failure

**Logger rate-limiting:**
- Max 20 Telegram messages per drain cycle
- If >20 queued: send first 20 + final INFO rollup ("N more events in logs")
- Anti-spam: no duplicate messages within 60s

---

## Agent Contract Structure

Each agent card includes:
1. **Emoji + Name + Mission** (one-liner)
2. **Purpose** (2–4 bullets)
3. **Allowed write paths** (explicit; outbox-only for most)
4. **Forbidden actions** (explicit)
5. **Required outputs** (schemas to produce)
6. **Event emission** (which statuses, always to outbox)
7. **Budgets** (files, MB, specs, stop threshold) — **STRICT CAPS**
8. **Stop conditions** (when to ask Ghosted)
9. **Inputs accepted** (links, spec paths, artifact IDs)
10. **What good looks like** (3 bullets)
11. **Security** (secrets, write-allowlist, destructive actions, execution isolation)
12. **Model recommendations** (Primary + Backup, or "none")

---

## See Also

- `agents/oq.md` through `agents/verifier.md` (individual contracts)
- `USER.md` (Operating Rules, Personality, Telegram Policy)
- `docs/RUNBOOKS/telegram-logging.md` (Logger implementation guide)
- `schemas/` (ResearchCard, IndicatorRecord, StrategySpec, BacktestReport, ActionEvent)
