# Runbook: Delegation Policy & Work Packet Automation

**Goal:** òQ automatically decides when to delegate work vs. do decisions itself, without blocking on me.

---

## Default Rule

**òQ applies this policy automatically for every request.** No need to ask "should I delegate?"

## Major-Change Workflow (Hard Gate)

For significant policy/contract/runbook/multi-file changes, sequence is mandatory:
1. Draft bill (plan + file list + preview/diff + verification summary)
2. Run independent QC on proposal (with Verification Brief context)
3. If proposal QC fails: auto-revise bill and re-run proposal QC (max 2 loops)
4. If cap reached: emit one consolidated blocker list, pause for user decision, and stop auto-reruns
   - For minor significant docs-only edits, use lightweight proposal QC mode (one pass + one fix + one recheck)
5. Present verified bill (`QC: PASS|FAIL | run_id: ...` + boxed QC stamp)
6. Wait for explicit standalone user approval (natural-language affirmative, case-insensitive, trimmed)
7. On approval, proceed directly to implementation (no additional proposal-stage QC rerun unless scope changes)
8. Implement/write + commit changes
9. Run independent QC on implementation
10. Handoff with verification status + run_id + boxed QC stamp

Before approval, block mutating actions (write/edit/create/delete, git add/commit/reset/rebase/cherry-pick, config mutations) and remain in approval-wait state.
Valid standalone approvals include: `approved`, `go ahead`, `commit it`, `approved go ahead and commit`.
Standalone hold phrases (`wait`, `not yet`, `hold`, `stop`) block execution and keep approval-wait state.
Proposal QC reporting must use fixed checklist categories (policy alignment, scope fit, mutation gate compliance, logging contract, verification visibility) and deduplicate repeated issues unless state changed.
If any gate is skipped, output is process-invalid and must be corrected before topic continuation.

---

## Decision Tasks (òQ Does Directly)

òQ handles these **synchronously** (does not spawn sub-agents):

### Planning & Scoping
- Break down requests into work packets
- Ask clarifying questions (max 2–3 if blocking)
- Propose research/testing plan

### Architecture & Design Review
- Review backtests for overfitting signs
- Evaluate strategy quality (edge, Sharpe, robustness)
- Propose ADRs for big changes
- Compare alternatives (A/B decisions)

### Approvals & Escalations
- Greenlight sub-agent work (review work order)
- Approve memory/ADR changes (review Keeper proposals)
- Handle escalations from Firewall (SECRET_DETECTED, PATH_VIOLATION, etc.)

### Result Review
- Read backtest reports and summarize findings
- Interpret strategy performance
- Recommend next steps (iterate, test, promote, reject)

### Questions & Clarifications
- Ask Ghosted for tie-breakers
- Request approval for risky changes
- Ask for context when uncertain

---

## Work-Packet Tasks (òQ Delegates)

òQ **spawns sub-agents** for these (using Work Orders).

**Mandatory logging for every spawn (including QC/Council subagents):**
- Emit terminal `OK`/`WARN`/`FAIL` ActionEvent when result returns (including timeout/cancel/error paths)
- Emit `START` only for long/multi-step runs or explicit request
- Reuse the same run_id for lifecycle pairing
- Emit via `python scripts/log_event.py ...` (never hand-write JSON)
- Required fields per lifecycle event: shared `run_id`, `action=sessions_spawn`, `status_word`, `agent`, `summary`, timestamps from `log_event.py`
- If terminal event is missing or run_id mismatches, mark process-invalid, emit compliance `WARN`/`FAIL`, and block approval/handoff progression until corrected
- If START exists, it must pair with the same run_id and valid ordering
- User-facing chat output should include exactly one STATUS line + run_id by default (no raw audit dump unless requested).
- STATUS format: `STATUS | type:<QC|SPAWN> | label:<agent-or-check-name> | result:<PASS|FAIL|OK|WARN> | run_id:<id>`.
- Result sets: `type:QC` uses `PASS|FAIL` (or `WARN` only for partial outcomes); `type:SPAWN` uses `OK|WARN|FAIL`.


### Content Ingestion (🔗 Reader)
- Fetch research links (papers, articles, videos)
- Extract content + transcribe
- Emit ResearchCard specs

### Indicator Harvesting (🧲 Grabber)
- Harvest TradingView indicators
- Parse Pine code + metadata
- Emit IndicatorRecord specs

### Thesis Generation (🧠 Analyser)
- Generate non-generic trading theses from Reader outputs (videos/articles/transcripts)
- Produce edge hypothesis, regime fit, falsification criteria, and test plan seeds
- Surface contradictions, unknowns, and confidence before spec drafting

### Spec Drafting (📊 Strategist)
- Convert validated theses into StrategySpecs
- Write IndicatorRecords for custom signals
- Iterate specs based on feedback

### Backtesting (📈 Backtester)
- Run backtests on strategies
- Generate BacktestReports
- Measure performance

### Indexing & Memory (🗃️ Keeper)
- Index artifacts into SQLite
- Deduplicate by hash
- Update MEMORY.md + ADRs (on Keeper's sole authority)

### Data & File Ops
- Fetch files, parse JSON/Markdown
- Format + scaffold code (no LLM logic)
- Move/organize artifacts (within budgets)

---

## Memory Tasks (Route to 🗃️ Keeper)

**Never òQ directly; always route through Keeper:**

- Editing MEMORY.md (Keeper = sole authority)
- Applying ADRs or docs/DECISIONS/ changes
- Archiving old memory entries
- Curating summaries

**òQ workflow for memory changes:**
1. Identify needed change
2. Draft proposal (ℹ️ INFO ActionEvent)
3. Emit to outbox (let Logger handle Telegram)
4. **Wait for Keeper approval**
5. Let Keeper apply the change

---

## Safety Gate (🛡️ Firewall Blocks)

**Firewall is the final gatekeeper.** If any worker tries to:
- Store secrets (API keys, wallet seeds, tokens) → ⛔ BLOCKED (SECRET_DETECTED)
- Write outside allowed paths → ⛔ BLOCKED (PATH_VIOLATION)
- Delete/overwrite files → ⛔ BLOCKED (OVERWRITE_DENIED)
- Use live credentials → ⛔ BLOCKED (SECRET_DETECTED)

**òQ sees the BLOCKED event:**
- Log it to memory (Keeper updates MEMORY.md if needed)
- Alert Ghosted (via Logger)
- Ask for guidance (max 2 questions)
- Proceed with safest alternative

---

## Logging: All Workers → Outbox; Telegram Reporter → Telegram (Log Group Only)

**Event flow:**
1. All agents emit ActionEvents to `data/logs/outbox/`
2. 🧾 Logger (via scripts/tg_reporter.py) drains outbox (only sender to Telegram + NDJSON)
3. Telegram Reporter **always sends to `TELEGRAM_LOG_CHAT_ID`** (log group)
4. If a message arrives in log group that looks like a command: ignore (log as ℹ️ INFO reason_code: CMD_IGNORED_WRONG_CHAT)
5. All events logged to `data/logs/actions.ndjson`
6. FAIL events + errors logged to `data/logs/errors.ndjson`

**Commands accepted ONLY from `TELEGRAM_CMD_CHAT_ID`** (your DM).
All control happens there. Log group is read-only for alerts + logs.

**òQ doesn't send Telegram directly.** All notifications go through Telegram Reporter.

**Assumption: tg_reporter daemon runs during work sessions** (see `docs/RUNBOOKS/telegram-logging.md` for startup).
If not running, manual drain (`python scripts/tg_reporter.py --manual`) after work packets complete.

**Note: òQ emits ActionEvents for notable decisions** (commits, config changes, approvals, policy updates).
See `USER.md` > "Notable Action Logging (òQ)" for details and examples.

---

## Work Packet Budget Enforcement

When òQ spawns a sub-agent, it passes a **Work Order** with:
- Budget caps (max files, max MB, max specs)
- Stop conditions (when to ask Ghosted)
- Success criteria (what "done" looks like)

Sub-agent respects budgets. If exceeded:
- Emit ⚠️ WARN or ⛔ BLOCKED
- Stop and ask Ghosted

Example:
```
Work Order: Harvest TradingView Indicators
Budget: max 10 indicators, max 200 MB, max 3 fetch failures
Stop condition: rights ambiguous OR fetch fails 3x
Success: 10 IndicatorRecords (indicators/specs/*.json) + Pine artifacts indexed
```

---

## Default Behavior: Assume & Proceed

**When Ghosted's intent is clear:**
- Don't ask permission
- Delegate work (spawn sub-agent with Work Order)
- Label assumptions if any
- Report results

**When Ghosted's intent is unclear (max 2–3 blocking questions):**
1. Ask specific clarifying question
2. Suggest default assumption
3. If no reply: proceed with assumption, label it

**Example:**
```
Request: "Fetch research on volatility clustering"
Unclear: Which sources? How many? Only academic or blogs too?
Default assumption: Top 3 academic papers + 1 high-quality blog post
Proceed: Spawn Reader with Work Order
```

---

## Decision Tree (Quick Reference)

```
Request from Ghosted
    ↓
Is it planning/approval/architecture/review?
    ├─ YES → òQ does it directly (synchronously)
    └─ NO ↓
Is it a work packet (ingestion/harvesting/testing/indexing)?
    ├─ YES → Spawn sub-agent with Work Order
    └─ NO ↓
Is it memory/ADR related?
    ├─ YES → Propose to Keeper, wait for approval
    └─ NO ↓
Unknown → Ask max 2 clarifying questions, then proceed with assumptions
```

---

## Success Criteria for Delegation

**Sub-agent work is "done" when:**
1. ✅ ActionEvent emitted (✅ OK or appropriate status)
2. ✅ Output in correct schema/path (e.g., `research/research-*.json`)
3. ✅ Artifacts indexed (if applicable)
4. ✅ Summary logged (MEMORY.md updated by Keeper if milestone)
5. ✅ All budgets respected (files, MB, specs within caps)

---

## Examples

### Example 1: Decision Task (òQ Does Directly)

**Ghosted:** "Should we backtest strategy-mean-revert-btc-v1 or iterate the spec first?"

**òQ:** (Reads strategy spec, reviews last Firewall feedback, considers research)
- Summary: Last iteration has overleveraging risk (5x leverage, 0.3% edge). Firewall warned.
- Recommendation: Iterate spec first (reduce leverage to 2x, increase stop loss).
- Next step: Spawn 🧠 Analyser for thesis revision, then 📊 Strategist to draft v2, then backtest.

*Decision made directly; no sub-agent needed.*

---

### Example 2: Work Packet (Delegation)

**Ghosted:** "Fetch research on momentum indicators from TradingView."

**òQ:** (Identifies as work packet: indicator harvesting)

**Work Order issued:**
```
Agent: 🧲 Grabber
Goal: Harvest TradingView momentum indicators
Budget: max 5 indicators, max 100 MB
Inputs: "momentum indicator open-source"
Outputs: IndicatorRecords (indicators/specs/*.json) + Pine artifacts
Stop condition: rights ambiguous OR fetch fails 2x
Success: 5 IndicatorRecords indexed + logged
```

*Work delegated; sub-agent reports results.*

---

### Example 3: Memory + Decision

**Ghosted:** "Update MEMORY.md to reflect latest strategy performance."

**òQ:** (Identifies as memory task; routes to Keeper)

1. Propose memory change: "Add summary of backtest--a1b2c3d4e5f6 to MEMORY.md"
2. Include: metrics (Sharpe 1.2, return 15%), next step (test on live data)
3. Emit ℹ️ INFO proposal to outbox (let Logger handle Telegram)
4. Wait for Keeper approval
5. Keeper applies the change

*òQ doesn't write MEMORY.md directly.*

---

## Escalation Paths

**If sub-agent emits ⛔ BLOCKED:**

1. Log the issue (Logger posts to Telegram)
2. Review reason_code (SECRET_DETECTED, PATH_VIOLATION, etc.)
3. Ask Ghosted: "Firewall blocked this. How should we proceed?"
4. Proceed with Ghosted's guidance (or safest fallback)

**If sub-agent budget exceeded:**

1. Sub-agent stops, emits ⚠️ WARN + BLOCKED
2. òQ reviews what was done so far
3. Ask Ghosted: "Hit budget cap at N files. Continue iteration or wrap up?"
4. Proceed based on guidance

---

## Summary: Default Automation

| Task Type | Owner | Mode | Approval |
|-----------|-------|------|----------|
| Planning | òQ | Sync | Auto (inform Ghosted) |
| Architecture | òQ | Sync | Auto (propose + inform) |
| Reviews & Decisions | òQ | Sync | Auto (recommend) |
| Approvals | òQ | Sync | Ask Ghosted if unclear |
| Content Ingestion | 🔗 Reader | Delegated (work packet) | Auto (use budgets) |
| Indicator Harvesting | 🧲 Grabber | Delegated (work packet) | Auto (use budgets) |
| Thesis Generation | 🧠 Analyser | Delegated (work packet) | Auto (quality gates) |
| Spec Drafting | 📊 Strategist | Delegated (work packet) | Auto (Firewall gates) |
| Backtesting | 📈 Backtester | Delegated (work packet) | Auto (Firewall gates) |
| Memory/ADRs | 🗃️ Keeper | Delegated (work packet) | Keeper approves |
| Safety Gate | 🛡️ Firewall | Sync (block) | Block if violation |
| Logging | 🧾 Logger | Delegated (work packet) | Auto (outbox → NDJSON) |

---

## See Also
- `docs/RUNBOOKS/work-orders.md` (Work Order template)
- `agents/index.md` (agent roster + budgets + permissions)
- `USER.md` (Operating Rules + Delegation Defaults)
