# AutoQuant — Project Memory

**Mission:** Build a durable, scalable "project brain" and automation-friendly memory system for a multi-agent trading R&D pipeline targeting Hyperliquid perps (execution later).

## North Star
- Avoid context explosion and file corruption
- Separate: Repo Memory (small, Git-tracked) + Artifact Store (large, immutable, NOT Git-tracked) + Retrieval Index (SQLite)
- **Specs vs Artifacts:** Git-track research/, strategies/specs/, indicators/specs/; Keep artifacts/ for bulky outputs only
- Files are source of truth; memory is the search layer
- Never store raw bulky artifacts in memory; use summaries + pointers + hashes

## Architecture (High-Level)
```
┌─ Repo Memory (MEMORY.md, docs/, schemas/, specs/) ──┐
│  • Compact, human-readable                            │
│  • Git-tracked, safe to commit                        │
│  • Index + North Star + Conventions + Decisions       │
└────────────────────────────────────────────────────┘
         ↓ references via hash/path
┌─ Artifact Store (artifacts/) ──────────────────────────┐
│  • Large immutable outputs only: videos, backtests     │
│  • Content-hashed, hash-first IDs                      │
│  • NOT Git-tracked; use .gitignore enforcement         │
└────────────────────────────────────────────────────┘
         ↓ indexed by
┌─ Retrieval Index (SQLite artifacts.db) ──────────────┐
│  • Fast metadata queries                              │
│  • Deduplication by hash                              │
│  • Links: artifact_id → path, summary, lineage        │
└────────────────────────────────────────────────────┘
```

## Key Invariants
1. **No secrets in memory** — API keys, tokens, private URLs live in .env / encrypted store only
2. **Immutable artifacts** — Never overwrite; new version = new hash, new ID, new row in index
3. **Summaries first** — Always retrieve compact summary; expand to raw chunks on demand
4. **Content hash = identity** — Dedup by hash automatically; IDs are `type--sha256_12`
5. **Specs vs Artifacts** — Git-track research/, strategies/specs/, indicators/specs/; artifacts/ = output only
6. **Windows-relative paths** — All paths use "/" convention; relative to repo root

## Conventions
- **Artifact ID format:** `{type}--{sha256_12}` (e.g., `backtest--a1b2c3d4e5f6`)
- **Optional date suffix:** `{type}--{sha256_12}_{date}` for readability if needed
- **Paths:** Use "/" everywhere; e.g., `artifacts/backtests/backtest--a1b2c3d4e5f6/metrics.json`
- **Schema instances:** Git-tracked specs in `research/`, `strategies/specs/`, `indicators/specs/`
- **Tags:** Flat list (e.g., `["hyperliquid", "perp", "live-test"]`); indexed in SQLite
- **Lineage:** Always store; tracks: `{ depends_on: [...], generated_by: "...", notes: "..." }`
- **Rights:** One of `open`, `restricted`, `unknown`; `attribution_required: bool`
- **Source URL:** Where did this come from? (repo link, paper URL, external dataset, etc.)

## Current Status
- [ ] Schemas finalized (ResearchCard, IndicatorRecord, StrategySpec, BacktestReport)
- [ ] SQLite retrieval index created
- [ ] First research cards added
- [ ] First backtest executed and indexed
- [ ] Backtest framework decision (Binance perps proxy → Hyperliquid cross-check)

## Quick Links
- Constitution: `docs/CONSTITUTION.md`
- Memory system ADR: `docs/DECISIONS/0001-memory-system.md`
- How to run: `docs/RUNBOOKS/00-how-to-run.md`
- Specs: `schemas/`, `research/`, `strategies/specs/`, `indicators/specs/`
- Artifacts: `artifacts/` (NOT Git-tracked)
- SQLite schema: `docs/SCHEMA-sqlite.md`

## Glossary
- **Repo Memory:** Small, Git-tracked files (MEMORY.md, schemas, docs, runbooks, specs)
- **Specs:** Source-of-truth definitions (research cards, indicator specs, strategy specs); Git-tracked
- **Artifact Store:** Large, immutable files (videos, backtests, datasets); NOT Git-tracked
- **Retrieval Index:** SQLite metadata layer for fast queries and deduplication
- **Content Hash:** SHA256 of artifact binary (12 chars in IDs); used for immutability + dedup
- **Lineage:** JSON object tracking dependencies: `{ depends_on: [...], generated_by: "...", notes: "..." }`
- **Rights:** `open` (shareable), `restricted` (internal only), `unknown` (clarify)
- **Signal Timing:** When does the indicator fire relative to candle close? (close, open next, EOD, etc.)
## System Infrastructure
### Telegram Logging (Live ✅)
- **tg_reporter daemon:** Automated via Windows Scheduled Task `AutoQuant-tg_reporter` (startup trigger)
- **Python PATH:** C:\Users\Clamps\AppData\Local\Programs\Python\Python314 (added to system PATH, permanent)
- **Credentials:** `.env` file (TELEGRAM_BOT_TOKEN, TELEGRAM_LOG_CHAT_ID, TELEGRAM_CMD_CHAT_ID) — no secrets in repo
- **Log group:** òQ LOG (chat ID: -5038734156) — receives all ActionEvents
- **Command chat:** Asz DM (chat ID: 1801759510) — for future command interface
- **Drain interval:** 15s (configurable; outbox → Telegram → actions.ndjson append)
- **Status:** Persistent; survives PowerShell close + system reboot

### Memory Polish Layer (New ✅)
- **memory_search.py:** Fast unified search across MEMORY.md + HANDOFFS + DAILY. Returns ranked results with file pointers + line ranges.
  - Usage: `python scripts/memory/memory_search.py "gateway auth" --limit 10`
  - Indexes by recency + file priority (MEMORY.md > HANDOFFS > DAILY)
- **handoff.schema.json:** Defines required/optional fields for JSON handoffs (ts_created, status, next_tasks required)
- **validate_handoff.py:** Validates + normalizes handoff files. Auto-fixes UTF-8, fills defaults, hard-fails on missing required fields.
  - Usage: `python scripts/handoff/validate_handoff.py <file> [--fix]`
- **make_daily_summary.py:** Generates daily session recap (docs/DAILY/YYYY-MM-DD-summary.md) + updates docs/STATUS.md
  - Captures: completed items, blockers, next actions, recent git changes, recent ActionEvents
  - Usage: `python scripts/daily/make_daily_summary.py` (run at end of session)
- **docs/STATUS.md:** Rolling "where are we at" page. Auto-updated by make_daily_summary.py
- **docs/DAILY/:** Daily session summaries (auto-generated)

## Keeper Promotions
- Phase 1: Logger + tg_reporter live and tested ✅ ([keeper:handoff:handoff-20260222-1234.md])
- All agents defined in roster; Reader is next build target ([keeper:handoff:handoff-20260222-1234.md])
- tg_reporter daemon now fully automated (Scheduled Task) ✅ ([keeper:handoff:handoff-20260222-2015.md])
- Model policy locked and synced to Codex primary, Haiku fallback, MiniMax manual-only ([keeper:handoff:handoff-20260222-2121.md])
- ✅ Telegram automation: Live + persistent (Scheduled Task) ([keeper:handoff:handoff-20260222-2030.md])
- ✅ Memory polish layer: Complete (search, validation, daily summaries) ([keeper:handoff:handoff-20260222-2030.md])
- ✅ All new scripts tested locally + committed ([keeper:handoff:handoff-20260222-2030.md])
- ⚠️ Gateway auth: Still shows "pairing required" (if reappears, use one-shot reset) ([keeper:handoff:handoff-20260222-2030.md])
- **Commit:** `8ba4742` — All new scripts + tests ([keeper:handoff:handoff-20260222-2030.md])

## Model Policy (Locked)
- Primary model: Codex 5.3
- Fallback model: Haiku
- Manual-only: MiniMax (excluded from automatic fallback)
- Active agents on Codex: Specter, Keeper, Strategist, Firewall, òQ
- Haiku-primary agents: Reader, Grabber
- Startup canonical rule: see USER.md → "Session Resume Contract (Canonical)"; do not duplicate startup procedures across docs.
