# AutoQuant/OpenClaw — Complete System Reference

## Architecture Overview

### Agent Fellowship
|Agent |Role |LLM |Interface |
|--------|------------------------------------------------|--------------------------|----------------------|
|Oragorn |Commander — read-only, delegates |GPT 5.3 |Telegram DM |
|Quandalf|Strategist — decides WHAT to trade |Claude Opus via CLI bridge|Telegram (Noodle + DM)|
|Frodex |Pipeline — executes, builds, backtests |OpenClaw Codex 5.3 |Telegram (Noodle + DM)|
|Balrog |Firewall — deterministic binary gates |None (PowerShell script) |Logs only |
|Smaug |Trader (future) — executes trades on HyperLiquid|TBD |TBD |

Chain of command: Oragorn oversees → Quandalf decides WHAT → Smaug decides WHEN/HOW → Balrog watches EVERYTHING → Asz approves major decisions.

### Communication Model
Agents communicate via FILES ONLY — never chat memory, never direct messaging:
- artifacts/strategy_specs/ — strategy specifications (JSON)
- artifacts/backtests/ — backtest results (JSON)
- artifacts/bundles/ — bundled research+thesis+spec packages
- artifacts/claude-specs/ — Quandalf-generated specs (staging area)
- docs/claude-reports/STRATEGY_ADVISORY.md — Quandalf’s advice to pipeline
- docs/claude-reports/DEEP_ITERATION_LOG.md — Quandalf’s trade-by-trade analysis
- docs/DOCTRINE/analyser-doctrine.md — accumulated rules and lessons
- data/logs/actions.ndjson — ALL pipeline events (timestamp field: ts_iso)
- data/logs/lessons.ndjson — structured lesson log for pattern detection
- data/logs/balrog/ — firewall violation logs

### Pipeline Flow
ResearchCard → Thesis → StrategySpec → BacktestResult → Lesson/Promotion → Refinement/OutcomeNotes
Each stage produces a JSON artifact.
The orchestrator (oQ) moves artifacts through stages.
The Backtester runs multiple variants per strategy via parameter sweeps (variants[] array).

### Scoring Formula (composite)
pf_score = min(profit_factor, 5.0) # capped to prevent overfit gaming
dd_penalty = min(max_drawdown_pct / 50, 1.0) # percentage-based drawdown cost
trade_factor = min(total_trades / 30, 1.0) # confidence from sample size
score = (pf_score * trade_factor) - dd_penalty - complexity_pen - gate_pen

### Backtester Metrics (all percentage-based, never dollars)
- pnl_pct — per-trade PnL as % of entry price
- max_drawdown_pct — peak-to-trough as % of peak equity
- total_return_pct — total equity change as % of first entry
- avg_trade_pnl_pct — average trade return %
- Position sizing currently hardcoded qty=1.0 (needs fixing)

### Best Result So Far
PF 2.01 — Quandalf spec claude-st19b8c4 supertrend_strong_trend ETH/4h
16 trades, $1502 PnL, 43.75% win rate, 2.6:1 win/loss ratio, 5.2% max drawdown
Key insight: “trade less, hold longer, extreme risk-reward ratios”
Needs walk-forward and multi-asset validation (must work on 3+ assets to confirm edge)

## Credential Locations — NEVER MIX UP
|What |File |Key Variables |
|-----------------------------|--------------------------------------|----------------------------------------------------------------------|
|Gateway bot (Frodex/pipeline)|workspace/.env |TELEGRAM_BOT_TOKEN, TELEGRAM_LOG_CHAT_ID, TELEGRAM_CMD_CHAT_ID |
|Quandalf bot (Claude bridge) |scripts/claude-bridge/.env |CLAUDE_BRIDGE_BOT_TOKEN, CLAUDE_BRIDGE_USER_ID, CLAUDE_BRIDGE_GROUP_ID|
|OpenClaw config |C:\Users\Clamps.openclaw\openclaw.json|Models, channels, agents |
|Destination |Chat ID |Which Bot |
|-----------------|---------------------|------------|
|oQ LOG channel |-5038734156 |Gateway bot |
|Noodle group |-1003841245720 |Both bots |
|Asz DM (Quandalf)|CLAUDE_BRIDGE_USER_ID|Quandalf bot|

## Scheduled Tasks (Windows Task Scheduler)
|Task |Agent |Frequency |What It Does |
|-----------------------------|--------|-------------|------------------------------------------------------------------------------|
|AutoQuant-Claude-Researcher |Quandalf|Every 4h |Cross-references backtests, market data, doctrine. Writes STRATEGY_ADVISORY.md|
|AutoQuant-Claude-Generator |Quandalf|Every 2h |Creates creative strategy specs in artifacts/claude-specs/ |
|AutoQuant-Claude-DeepIterator|Quandalf|Every 4h |Trade-by-trade analysis of recent backtests. Writes DEEP_ITERATION_LOG.md |
|AutoQuant-Claude-Doctrine |Quandalf|Daily 4am |Synthesizes lessons into doctrine rules |
|AutoQuant-Claude-Auditor |Quandalf|Daily 5am |Audits backtest integrity and methodology |
|AutoQuant-Claude-Bridge |Quandalf|Always on |Telegram bot for natural chat with Quandalf |
|Autopilot (pipeline) |Frodex |Every ~15 min|Full pipeline cycle: grab → analyse → strategise → backtest → refine → promote|
|Bundle Run Log |System |Every 15 min |Sends summary of pipeline cycle to log channel with agent banner |

## Key Design Principles

### Logician Pattern (from Resonant OS)
Separate probabilistic (LLM) from deterministic (code) at EVERY step:
- LLM decides WHAT (creative, strategic) → deterministic script validates it happened (binary gate)
- Specs must parse as valid JSON with required fields before entering pipeline
- Backtest results must contain real numbers, not just “looks good”
- Test = evidence (file exists, numbers are real), not LLM saying it checked
- Track mistakes in structured logs → detect patterns → auto-create rules
- Balrog is a SCRIPT with binary gates, NOT an LLM agent

### Self-Improvement Loop
1. Every agent logs structured lessons to lessons.ndjson
1. Pattern detection script scans for recurring errors (3+ occurrences)
1. Patterns become doctrine rules or Balrog gates automatically
1. Rules get tested — if same failure occurs WITH the rule, rule is broken → update it
1. System gets tighter over time without human intervention

### Model Reasoning Policy
Central policy at config/model_reasoning_policy.json defines 4 buckets:
- system: no LLM, deterministic scripts (logging, backtesting, file ops)
- low: cheap utility (Haiku-level, dedup checks, simple summaries)
- medium: default quality (strategy decisions, analysis, generation)
- high: deep synthesis (research, doctrine, critical audits)

Every task is mapped to a bucket.
Resolver: scripts/automation/resolve_model_policy.py
Drift guard: scripts/tests/test_model_policy.py ensures no unmapped tasks exist.

### Delegation Protocol
- Quandalf max 100 lines code. Delegates bigger work to Frodex.
- When delegating, ALWAYS include: WHY (business context), WHAT (data/evidence), HOW (specific instructions), DONE (success criteria), DOCS (relevant documentation)
- Specs include description field explaining reasoning, not just parameters

### Future-Proofing
- Don’t add rigid rules that constrain future capability
- HyperLiquid adds new instruments — agents should explore whatever makes money
- Strategy must work on 3+ assets to confirm edge (prevent overfitting)
- Percentages over dollars for ALL metrics (qty=1.0 is hardcoded)
- Analyser SOUL.md designed to evolve toward hedge fund manager brain

## Event Log Format (actions.ndjson)
CRITICAL: Timestamp field is ts_iso, NOT ts
Fields: ts_iso, ts_local, run_id, agent, model_id, action, status_word, reason_code, summary

Oragorn commander identity for emitted events:
- agent = `Oragorn`
- model_id = `gpt-5.3-codex`

Oragorn-required actions:
- DELEGATION_SENT
- SUBAGENT_SPAWNED
- DIAGNOSIS_COMPLETE
- CONTEXT_UPDATE

Key summary events and their formats:
- GRABBER_SUMMARY → “Grabber: fetched=N dedup=N failed=N”
- BATCH_BACKTEST_SUMMARY → “Batch: runs=N executed=N skipped=N”
- LIBRARIAN_SUMMARY → “Library: top=N run=N lessons=N new=N archived=N”
- PROMOTION_SUMMARY → “Promote: bundles=N variants=N status=…”
- REFINEMENT_SUMMARY → “Refine: iters=N variants=N explore=N delta=…”
- DIRECTIVE_LOOP_SUMMARY → “Directive loop: notes=N directive_variants=N exploration_variants=N”
- DIRECTIVE_LOOP_STALL_WARN → stall cycle count (pipeline stuck)
- LAB_STARVATION_WARN → starvation count (no new input)
- LAB_SUMMARY → “Lab: ingested=N … errors=N”
- INSIGHT_SUMMARY → “Insight: new_processed=N revisited=N”
- DIRECTIVE_GEN_FAIL → strategist failed to generate variants

### Reading Pipeline Health
When asked “how’s the pipeline” or similar, read the last 50 lines of actions.ndjson and report:
- Are videos being grabbed? (fetched > 0)
- Are backtests running? (executed > 0)
- Are strategies being promoted? (promoted > 0)
- Is the directive loop producing variants? (directive_variants > 0)
- Any stall or starvation warnings?
- Any errors or Balrog blocks?

## Config Locations
C:\Users\Clamps\.openclaw\openclaw.json — OpenClaw main config
C:\Users\Clamps\.openclaw\workspace\ — Workspace root
C:\Users\Clamps\.openclaw\workspace\.env — Gateway tokens + channel IDs
C:\Users\Clamps\.openclaw\workspace\scripts\claude-bridge\.env — Quandalf bot tokens
C:\Users\Clamps\.openclaw\workspace\assets\banners\ — Agent banner images for bundle log
C:\Users\Clamps\.openclaw\workspace\config\ — Policy files

## PowerShell 5.1 Compatibility
System runs Windows PowerShell 5.1.
When reviewing or delegating script work:
- No ?? null-coalescing → use if/else
- No ?. null-conditional → use if ($obj) { $obj.Property }
- No ??= null-coalescing assignment → standard if/else

## Live Pipeline Snapshot (auto-updated)
Generated: 2026-03-01 10:06 UTC

- Recent events window: last 50 ActionEvents
- Grabber fetched: 2
- Backtests executed: 7
- Promoted variants: 4
- Directive variants: 4
- Stall cycles: 0
- Starvation cycles: 0
- Error events: 0

Artifact state:
- strategy_specs: 1
- backtests: 0
- bundles: 1
- claude-specs (staging): 0

## Known Issues (auto-updated)
- No critical issues detected in the recent deterministic window.

## Roadmap Progress (auto-updated)
- Model policy Phase 1 (policy + resolver + drift guard): ✅ active
- Model policy Phase 2 (script wiring references): 2 script(s) currently reference the resolver
- Oragorn context auto-sync: ✅ enabled (daily target 03:00)
- Doctrine source size: 40 lines
- Strategy advisory source size: 269 lines
- Refactor backtest auditor — replace most Claude checks with deterministic script _(log 2026-03-01T10:04:53.4017593Z)_
## Roadmap
- Phase 2: Wire model_reasoning_policy.json resolver into all scripts
- Refactor backtest auditor — replace most Claude checks with deterministic script, only send edge cases to Claude for narrative interpretation. Most audit checks are pure math that don't need an LLM.
- Position sizing (variable qty based on confidence/risk)
- Walk-forward analysis for strategy validation
- Trailing stops
- SQLite integration improvements
- Gaussian strategy research
- Specter completion (partial)
- Live execution via HyperLiquid API
- Market brain / hedge fund manager evolution
- Smaug trader agent
- YouTube watcher expansion: IntoTheCryptoverse, ECKrown, TradeTravelChill
- Daily Intel Brief evolution: direct Telegram messages with AI-generated contextual images + audio summaries
- Balrog pipeline health gates (stall/starvation detection + auto-alerting)
