# Work Order Template

**Purpose:** Standard form òQ uses when delegating work to sub-agents.

---

## Work Order Format

```
═══════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════

Agent: [🔗 Reader | 🧲 Grabber | 🧠 Analyser | 📊 Strategist | 📈 Backtester | 🗃️ Keeper]
Priority: [normal | high]
Deadline: [time limit or "ASAP"]

───────────────────────────────────────────────────────────────
GOAL
───────────────────────────────────────────────────────────────
[One-liner: what success looks like]

───────────────────────────────────────────────────────────────
INPUTS
───────────────────────────────────────────────────────────────
- [Link / file path / spec ID / data source]
- [Additional inputs as needed]

───────────────────────────────────────────────────────────────
OUTPUTS (Exact Paths + Schemas)
───────────────────────────────────────────────────────────────
- [Path 1: e.g., research/research-volatility-20260222.json (ResearchCard schema)]
- [Path 2: e.g., indicators/specs/indicator-example-v1.json (IndicatorRecord schema)]
- [ActionEvent to spool: status ✅ OK or ❌ FAIL + reason_code]

───────────────────────────────────────────────────────────────
BUDGET CAPS
───────────────────────────────────────────────────────────────
Max files: [N]
Max MB: [N]
Max specs/cards: [N]
Stop-ask threshold: [condition]

───────────────────────────────────────────────────────────────
STOP CONDITIONS (Ask Ghosted if any hit)
───────────────────────────────────────────────────────────────
- [e.g., "Rights unclear or source unreachable"]
- [e.g., "Fetch fails 3x"]
- [e.g., "Generic idea detected"]

───────────────────────────────────────────────────────────────
SUCCESS CRITERIA
───────────────────────────────────────────────────────────────
- [ ] Output in correct schema/path
- [ ] ActionEvent emitted (✅ OK or appropriate status)
- [ ] Budgets respected (files, MB, specs within caps)
- [ ] All stop conditions avoided OR escalated to Ghosted
- [ ] Summary logged (if applicable)

───────────────────────────────────────────────────────────────
NOTES
───────────────────────────────────────────────────────────────
[Optional context for the agent]

═══════════════════════════════════════════════════════════════
```

---

## Example Work Orders

### Example 1: Reader (Content Ingestion)

```
═══════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════

Agent: 🔗 Reader
Priority: normal
Deadline: ASAP

───────────────────────────────────────────────────────────────
GOAL
───────────────────────────────────────────────────────────────
Fetch research on volatility mean-reversion strategies and emit ResearchCard(s)

───────────────────────────────────────────────────────────────
INPUTS
───────────────────────────────────────────────────────────────
- "volatility mean reversion trading strategy"
- (Fetch 2–3 high-quality sources: academic papers or well-cited blogs)

───────────────────────────────────────────────────────────────
OUTPUTS
───────────────────────────────────────────────────────────────
- research/research-volatility-mean-revert-20260222.json (ResearchCard schema)
- Optional: artifacts/videos/video--{hash}/ (if transcript available)
- ActionEvent to spool: ✅ OK (fetched + ResearchCard written)

───────────────────────────────────────────────────────────────
BUDGET CAPS
───────────────────────────────────────────────────────────────
Max files: 3
Max MB: 100
Max ResearchCards: 2
Stop-ask threshold: Fetch timeout OR rights unclear

───────────────────────────────────────────────────────────────
STOP CONDITIONS
───────────────────────────────────────────────────────────────
- Source returns 404 / 403 → FAIL (SOURCE_UNREACHABLE)
- License unknown → WARN, ask Ghosted before using
- Transcript fails → FAIL (TRANSCRIPT_FAIL), suggest alternative

───────────────────────────────────────────────────────────────
SUCCESS CRITERIA
───────────────────────────────────────────────────────────────
- [ ] ResearchCard JSON in research/ with testable hypothesis
- [ ] Findings extracted (100–300 words)
- [ ] Confidence level set (high/medium/low)
- [ ] Tags included (e.g., ["volatility", "mean-reversion", "signal-design"])
- [ ] ActionEvent emitted (✅ OK)

───────────────────────────────────────────────────────────────
NOTES
───────────────────────────────────────────────────────────────
Prefer peer-reviewed sources. Note any open questions in ResearchCard.

═══════════════════════════════════════════════════════════════
```

### Example 2: Analyser (Thesis Generation)

```
═══════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════

Agent: 🧠 Analyser
Priority: high
Deadline: ASAP

───────────────────────────────────────────────────────────────
GOAL
───────────────────────────────────────────────────────────────
Turn Reader outputs into a non-generic, testable thesis package for strategy drafting

───────────────────────────────────────────────────────────────
INPUTS
───────────────────────────────────────────────────────────────
- research/research-volatility-mean-revert-20260222.json
- Transcript notes from Reader

───────────────────────────────────────────────────────────────
OUTPUTS
───────────────────────────────────────────────────────────────
- artifacts/analysis/thesis-volatility-mean-revert-v1.md
- ActionEvent to spool: ✅ OK (thesis package produced) or ⚠️ WARN (generic/low confidence)

───────────────────────────────────────────────────────────────
SUCCESS CRITERIA
───────────────────────────────────────────────────────────────
- [ ] Edge hypothesis clearly stated
- [ ] Regime fit + invalid conditions specified
- [ ] Falsification tests listed
- [ ] Concrete backtest seed passed to 📊 Strategist

═══════════════════════════════════════════════════════════════
```

### Example 3: Strategist (Spec Drafting)

```
═══════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════

Agent: 📊 Strategist
Priority: high
Deadline: ASAP

───────────────────────────────────────────────────────────────
GOAL
───────────────────────────────────────────────────────────────
Design StrategySpec for volatility mean-reversion strategy using volatility z-score indicator

───────────────────────────────────────────────────────────────
INPUTS
───────────────────────────────────────────────────────────────
- research/research-volatility-mean-revert-20260222.json
- indicators/specs/indicator-volatility-zscore-v1.json
- Previous feedback: "reduce leverage from 5x to 2x, increase stop loss"

───────────────────────────────────────────────────────────────
OUTPUTS
───────────────────────────────────────────────────────────────
- strategies/specs/strategy-volatility-mean-revert-btc-v2.json (StrategySpec schema)
- ActionEvent to spool: ✅ OK (spec written + passed Firewall) or ⚠️ WARN (marginal pass) or ❌ FAIL (blocked)

───────────────────────────────────────────────────────────────
BUDGET CAPS
───────────────────────────────────────────────────────────────
Max files: 2
Max MB: 2
Max StrategySpecs: 1
Stop-ask threshold: Generic idea OR untestable

───────────────────────────────────────────────────────────────
STOP CONDITIONS
───────────────────────────────────────────────────────────────
- Firewall rejects spec → escalate reason_code to Ghosted
- Spec passes but feels generic → ask Ghosted for clarification
- Leverage still >3x → ask Ghosted for constraints

───────────────────────────────────────────────────────────────
SUCCESS CRITERIA
───────────────────────────────────────────────────────────────
- [ ] StrategySpec JSON in strategies/specs/
- [ ] Entry rules: specific, testable (e.g., "when vol_z_score > 2.0 AND price > SMA20")
- [ ] Exit rules: clear (e.g., "when vol_z_score < 1.0 OR loss > 2%")
- [ ] Risk params: leverage ≤ 2x, max_loss_pct 2, max_position_usd 5000
- [ ] Indicators array populated (link to volatility-zscore-v1)
- [ ] Status: "draft" (ready for backtest)
- [ ] Passed Firewall (✅ OK)
- [ ] ActionEvent emitted

───────────────────────────────────────────────────────────────
NOTES
───────────────────────────────────────────────────────────────
Iterate on v1 feedback. If Firewall blocks: stop and report reason.

═══════════════════════════════════════════════════════════════
```

### Example 4: Backtester (Execution)

```
═══════════════════════════════════════════════════════════════
WORK ORDER
═══════════════════════════════════════════════════════════════

Agent: 📈 Backtester
Priority: normal
Deadline: ASAP (target <5 min)

───────────────────────────────────────────────────────────────
GOAL
───────────────────────────────────────────────────────────────
Run backtest on strategy-volatility-mean-revert-btc-v2 using 2024 Binance BTC/USDT 1m data

───────────────────────────────────────────────────────────────
INPUTS
───────────────────────────────────────────────────────────────
- strategies/specs/strategy-volatility-mean-revert-btc-v2.json
- Dataset: data-binance-btc-2024
- Timeframe: 1m
- Date range: 2024-01-01 to 2024-12-31

───────────────────────────────────────────────────────────────
OUTPUTS
───────────────────────────────────────────────────────────────
- artifacts/backtests/backtest--{hash}/ (folder with metrics.json, equity_curve.csv, trades.csv, config.json)
- BacktestReport schema (metrics: total_return, sharpe, max_dd, win_rate, trades)
- ActionEvent to spool: ✅ OK (completed) or ⚠️ WARN (suspicious metrics) or ❌ FAIL (timeout/error)

───────────────────────────────────────────────────────────────
BUDGET CAPS
───────────────────────────────────────────────────────────────
Max backtests: 1
Max runtime: 300 seconds
Max output MB: 200
Stop-ask threshold: Timeout OR suspected overfitting

───────────────────────────────────────────────────────────────
STOP CONDITIONS
───────────────────────────────────────────────────────────────
- Timeout after 300s → FAIL (TIMEOUT)
- Sharpe < 0.5 AND win_rate < 45% → WARN (LOW_EDGE), ask Ghosted
- Max_dd > 30% → WARN (HIGH_DD), ask Ghosted
- Overfitting suspected → BLOCKED, ask Ghosted for guidance

───────────────────────────────────────────────────────────────
SUCCESS CRITERIA
───────────────────────────────────────────────────────────────
- [ ] BacktestReport JSON in artifacts/backtests/{id}/
- [ ] Metrics include: total_return, sharpe, max_dd, win_rate, profit_factor, trades
- [ ] Equity curve CSV + trade log CSV included
- [ ] config.json included (for reproducibility)
- [ ] All fees, slippage, commissions included
- [ ] Paper trading mode (no live credentials)
- [ ] Completed in <5 minutes
- [ ] ActionEvent emitted

───────────────────────────────────────────────────────────────
NOTES
───────────────────────────────────────────────────────────────
Use Binance fee model (0.1% maker/taker). Include 0.01% slippage.

═══════════════════════════════════════════════════════════════
```

---

## Work Order Lifecycle

1. **òQ creates Work Order** (this template)
2. **Sub-agent receives Work Order** (e.g., 🧲 Grabber)
3. **Sub-agent executes** (respects budgets, follows outputs/success criteria)
4. **Sub-agent emits ActionEvent** (✅ OK, ⚠️ WARN, ❌ FAIL, or ⛔ BLOCKED)
5. **Logger drains ActionEvent** (posts to Telegram, appends to NDJSON)
6. **òQ reviews results** (read output, check success criteria, decide next step)
7. **òQ reports to Ghosted** (summary + recommendation)

---

## See Also
- `docs/RUNBOOKS/delegation-policy.md` (decision tree + default behavior)
- `agents/index.md` (agent roster + budgets)
- `USER.md` (Delegation Defaults section)
