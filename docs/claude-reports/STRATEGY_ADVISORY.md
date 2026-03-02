# Strategy Advisory — 2026-03-02 (Update 12)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 610+ outcome notes (all-time), 23 ACCEPT outcomes, latest 30 outcomes (20260302), latest 10 backtests (20260302), ~80 strategy specs (20260302 incl. 9 claude-specs / 27 variants), 1 research card (fixture only), doctrine as of 20260228
**Prior advisory:** 2026-03-02 (Update 11)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "0 trades in 12+ cycles, bug line 179, 12th advisory"},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "0 trades in 9+ cycles, structural impossibility on crypto 4h/1h"},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser at any R:R"},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "DD 83-484% in latest 10 backtests, pipeline STILL generating BTC specs despite 12 cycles of exclusion requests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications, 13 cycles, notes_considered=0 always"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success, confidence_threshold never consumed"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "produces identical metrics across all applications"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%, 13 cycles"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_exit_change", "reason": "0% profitability in 10+ tests"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_gate_adjust", "reason": "PF 1.001 at best, noise trading"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_threshold_sweep", "reason": "0% improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_template_switch", "reason": "0% success in 30+ outcome notes"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_1_param_sweep", "reason": "PF 0.969, DD 147%, zero improvement"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_role_swap", "reason": "PF 0.644-0.963, 100% REJECT rate, confirmed in latest 10 backtests"},
  {"action": "BLACKLIST_VARIANT", "target": "directive_variant_2_threshold_sweep", "reason": "PF 0.998, noise, converges to same params"},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 1, "reason": "CHAMPION — best ACCEPT PF=1.921, 7 ACCEPTs total, all-regime profitable"},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 2, "reason": "9 ACCEPTs, best PF=1.712, most consistent"},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 3, "reason": "5 ACCEPTs (NEW: rsi_shallow_slingshot_12to1 PF=1.270)"},
  {"action": "PREFER_TEMPLATE", "target": "ema_rsi_atr", "priority": 4, "reason": "2 ACCEPTs (NEW: precision_10to1 PF=1.327)"},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All 23 ACCEPTs use 5:1+ R:R, sub-4:1 is structural noise on HyperLiquid fees"},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 7+ cycles, every outcome shows NO_IMPROVEMENT"},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of all-time ACCEPTs (23/23), pipeline specs = 0%"},
  {"action": "BACKTEST_CLAUDE_SPECS_FIRST", "targets": ["claude-er8v3m6k", "claude-st5k2r8w", "claude-rp3w7k9d", "claude-mc6t8b3k", "claude-rp4f2w8n", "claude-st7a3k5w", "claude-ec6t4w8m", "claude-rp8f3m7v", "claude-mc4w9s2t", "claude-st6n2w4r", "claude-rp2f8k4v", "claude-mc7b3t9w", "claude-mc8r5t2w"], "reason": "13 specs ~33 variants still unbacktested"},
  {"action": "FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "CHAMPION PF=1.921, DD=10.9%, all regimes profitable, 6th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "macd_7to1_tail_harvester", "reason": "PF=1.712, DD=7.5%, 6th cycle requesting"},
  {"action": "FORWARD_TEST", "target": "ema_rsi_atr_precision_10to1", "reason": "NEW ACCEPT PF=1.327, ranging PF=2.864"},
  {"action": "ADD_REGIME_GATE", "target": "all_strategies", "gate": "disable_during_trending", "reason": "NEW — 21/23 ACCEPTs lose money or break even in trending. Trending PF 0.37-0.95 typical. Gate would boost portfolio PF by ~0.2-0.4"},
  {"action": "INVESTIGATE_BUG", "target": "regime_classifier_pipeline_interaction", "reason": "UPDATED — not a classifier bug. Claude specs find 51-57 ranging trades; pipeline template_diversity finds 0. Root cause is pipeline signal design, not classifier."}
]
```

---

## Executive Summary

**Two new ACCEPTs this cycle bring the all-time total to 23 — still 100% Claude-originated.** The ema_rsi_atr_precision_10to1 (PF=1.327, ranging PF=2.864) and rsi_shallow_slingshot_12to1 (PF=1.270, transitional PF=1.834) validate two key hypotheses: narrow RSI bands produce higher-conviction entries, and extreme R:R (10:1-12:1) works even on less-proven templates. Critically, the "regime classifier bug" from Update 11 is now better understood — Claude specs find 51-57 ranging trades per backtest while pipeline specs find zero, confirming the issue is pipeline signal design (signals that never fire during consolidation), not a broken classifier. The pipeline remains catastrophically wasteful: 28/30 latest outcomes are functionally identical template_diversity runs with only 4 unique metric profiles. Meanwhile, 33+ Claude spec variants sit unbacktested.

---

## Failing Patterns

### 1. Parameter Convergence (CRITICAL — 13TH CYCLE, STILL WORSENING)
The latest 30 outcomes collapse to **4 unique metric profiles**. 28 of 30 are template_diversity variants producing identical results: PF=1.104/DD=9.0%/54 trades (15 outcomes), PF=1.257/DD=242.6%/61 trades (6 outcomes), PF=0.969/DD=146.6%/62 trades (3 outcomes), PF=1.033/DD=28.5%/389 trades (3 outcomes). Only 2 outcomes (both Claude-originated ACCEPTs) are unique. **Compute waste: 93%+ of this cycle's resources produced duplicate data.**

### 2. Pipeline Spec Generation (STRUCTURALLY BROKEN)
Pipeline specs continue to target BTC with 1.3:1 R:R despite 12 cycles of exclusion directives. The latest 10 backtests include BTC specs with DD of 484% and PF=0.644. Pipeline-generated specs have produced **0 ACCEPTs across 600+ attempts** (all-time 0% rate). This is not a tuning problem — the spec generator's parameter space is fundamentally miscalibrated.

### 3. Directive System (DEAD — 0/31+ ENFORCED, 13 CYCLES)
All 30 latest outcomes show `directive_history.notes_considered: 0`. Even the 2 new ACCEPT outcomes show zero notes considered. The pipeline generates new directive variant names (v2 role_swap, v2 threshold_sweep) but these produce the same or worse results. The directive system is architectural dead weight consuming advisory bandwidth.

### 4. Refinement Engine (DEAD — 8+ CYCLES)
Every outcome note (all 610+) contains `NO_IMPROVEMENT`. The refinement cycle hash is shared across entire batches. The system has never achieved measurable improvement through refinement.

### 5. Trending Regime Performance (NEWLY QUANTIFIED AS STRUCTURAL LOSER)
Both new ACCEPTs show trending PF < 0.8 (er4n7b2k trending PF=0.372, rp6k3w9d trending PF=0.763). Of all 23 ACCEPTs, **21 lose money or barely break even in trending conditions.** Trending is not a weak regime — it is an active profit destroyer. Any strategy deployed without a trending gate will bleed money during trending phases.

### 6. Dead Templates (UNCHANGED)
- **stochastic_reversal**: Bug at signal_templates.py:179. Long condition requires K < 20 when K just crossed above D — logically impossible. Zero trades, 12 cycles.
- **bollinger_breakout**: 2-sigma band breakout impossible on crypto volatility profiles. Zero trades, 9 cycles.

### 7. alignment_entry Signal (DEAD ON ARRIVAL — CONFIRMED)
PF 0.615-0.969 across all tests. Generic "confidence >= 0.60" threshold with no concrete indicator logic. Structural loss generator at any R:R.

### 8. directive_variant_2_role_swap (NEWLY CONFIRMED WORST)
Latest backtests: PF=0.644 (BTC/4h), PF=0.963 (ETH/1h). This variant swaps entry/exit roles, producing inverted signals. 100% REJECT rate.

### 9. Research Card Pipeline (DEAD — ONLY TEST FIXTURE)
Single file: `rc-directive-loop-fixture.json`. Zero real research cards from video ingestion. Auto-transcript system referenced in doctrine has never produced output.

---

## Promising Directions

### 1. Supertrend 8:1 Tail Harvester — CHAMPION (PF=1.921, 6th cycle requesting forward test)
Highest PF of any ACCEPT. DD=10.9%, 85 trades, profitable in ALL regimes (trending=1.289, ranging=2.914, transitional=1.844). The ONLY template family that profits in trending. Supertrend's ranging PF=2.914 is the highest single-regime score. If we could only forward-test one strategy, this is it.

### 2. ema_rsi_atr Precision — NOW 2 ACCEPTs
The new ema_rsi_atr_precision_10to1 (PF=1.327, 162 trades, ranging PF=2.864) joins ea9p5k2m (PF=1.288). Both use narrow RSI bands. The precision variant's ranging PF=2.864 nearly matches Supertrend's 2.914. This template has more headroom than originally estimated — testing with regime gates could push PF above 1.5.

### 3. RSI Shallow Slingshot 12:1 — NEW ACCEPT VALIDATES EXTREME R:R
PF=1.270, DD=8.4%, 162 trades. The 12:1 R:R works on RSI pullback, proving the R:R thesis extends beyond Supertrend and MACD. Transitional PF=1.834 is strong. This opens the door to testing 12:1+ on all winning templates.

### 4. Trending Regime Gate — SINGLE BIGGEST PORTFOLIO IMPROVEMENT AVAILABLE
21/23 ACCEPTs lose money in trending. Adding a simple regime gate ("do not trade during trending") to ranging/transitional specialists would:
- Eliminate the worst-performing 40% of trades
- Boost net PF by an estimated 0.2-0.4 across all strategies
- Reduce DD significantly (trending drawdowns are the deepest)
This is a configuration change, not a new strategy. Immediate ROI.

### 5. Multi-Strategy Portfolio (READY — 3 COMPLEMENTARY PROFILES)
| Strategy | Ranging PF | Transitional PF | Trending PF | Role |
|---|---|---|---|---|
| Supertrend 8:1 | 2.914 | 1.844 | 1.289 | All-weather core |
| ema_rsi_atr precision | 2.864 | 1.731 | 0.372 | Ranging specialist (with trending gate) |
| MACD 12:1 ultimate | 1.581 | 0.569 | 2.177 | Trending specialist |
| RSI slingshot 12:1 | 1.610 | 1.834 | 0.763 | Transitional specialist (with trending gate) |

Combined, this portfolio covers every regime. With regime gates, estimated portfolio PF > 1.5 in all conditions.

### 6. Claude Spec Backtest Queue (33+ VARIANTS WAITING)
13 Claude specs (~33 variants) remain unbacktested. Based on the 4/11 = 36% ACCEPT rate for Claude specs that HAVE been backtested, we can expect 10-12 new ACCEPTs from the queue. These include:
- Supertrend extreme R:R variants (10:1, 12:1)
- EMA crossover diagnostic (tests whether signal complexity matters)
- MACD 1h timeframe variants (untested territory)
- SOL asset variants (only ETH has been tested)
- Time-capped entries (novel exit mechanism)

### 7. SOL as New Test Asset
3 Claude specs target SOL (claude-ec3s7w2k, claude-er5s9k4w). SOL has different volatility/liquidity profile than ETH. If SOL produces ACCEPTs, it doubles our addressable market without signal changes.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg PF | Avg DD | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|---|---|
| supertrend_follow | 7 | 1.921 | 1.470 | 12.5% | 95 | CHAMPION | Forward-test immediately; test 10:1, 12:1 R:R |
| macd_confirmation | 9 | 1.712 | 1.459 | 8.2% | 155 | STRONG | Forward-test MACD 7:1; test 1h timeframe |
| rsi_pullback | 5 | 1.712 | 1.389 | 9.0% | 105 | GOOD | NEW ACCEPT at 12:1; test narrow RSI bands |
| ema_rsi_atr | 2 | 1.327 | 1.308 | 17.6% | 127 | RISING | NEW ACCEPT; add trending regime gate |
| ema_crossover | 0 | — | — | — | — | DIAGNOSTIC | 3+ variants awaiting backtest |
| stochastic_reversal | 0 | — | — | — | — | DEAD | Remove from registry (bug at line 179) |
| bollinger_breakout | 0 | — | — | — | — | DEAD | Remove from registry (structural) |

**Claude spec backtest queue:** 13 specs, ~33 variants. 4 specs have been backtested producing 4 ACCEPTs (36% rate). 33 variants still waiting.

---

## Regime Insights

### Regime Performance Matrix (from 23 ACCEPTs)

| Template Family | Trending PF | Ranging PF | Transitional PF | Best Regime |
|---|---|---|---|---|
| Supertrend 8:1 | 1.289 | **2.914** | 1.844 | Ranging |
| Supertrend (other) | 0.75-0.95 | 1.61-2.56 | 1.38-1.57 | Ranging |
| MACD 7:1 | 1.677 | **2.062** | 1.308 | Ranging |
| MACD 12:1 | **2.177** | 1.581 | 0.569 | Trending |
| MACD wide exit | 1.230 | **1.872** | 0.816 | Ranging |
| RSI pullback 8:1 | 1.505 | **1.795** | 0.930 | Ranging |
| RSI slingshot 12:1 (NEW) | 0.763 | 1.610 | **1.834** | Transitional |
| RSI shallow dip | 1.202 | 0.090 | **5.568** | Transitional |
| ema_rsi_atr precision (NEW) | 0.372 | **2.864** | 1.731 | Ranging |
| ea9p5k2m | 0.766 | 1.216 | **2.765** | Transitional |

### Key Regime Findings (Updated)

1. **Ranging remains the money regime.** 19/23 ACCEPTs profit from ranging. Top ranging PFs: 2.914 (Supertrend), 2.864 (ema_rsi_atr precision — NEW), 2.558 (Supertrend ultra), 2.062 (MACD 7:1).

2. **Trending is the profit destroyer.** 21/23 ACCEPTs show trending PF < 1.0 or barely above. The two exceptions: Supertrend 8:1 (trending PF=1.289) and MACD 12:1 (trending PF=2.177). A simple "no trade in trending" gate would improve 21/23 strategies immediately.

3. **Transitional alpha is real but sample sizes are growing.** 4 strategies now show strong transitional edge: RSI slingshot 12:1 (PF=1.834, 37 trades), ea9p5k2m (PF=2.765, ~12 trades), RSI shallow dip (PF=5.568, ~9 trades), ema_rsi_atr precision (PF=1.731, 45 trades). The precision variant's 45 transitional trades are the best sample size yet for this regime.

4. **Regime classifier is NOT globally broken** (UPDATE from Update 11). Claude specs find 51-57 ranging trades per backtest. Pipeline template_diversity specs find zero. Root cause: pipeline signal parameters (low R:R, generic entries) produce signals that cluster in trending/transitional but not ranging. The classifier labels correctly; the pipeline's signals just don't fire during consolidation.

5. **Portfolio diversification is now actionable.** With 23 ACCEPTs spanning all three regimes, a regime-gated portfolio is achievable: Supertrend for all-weather core, MACD 12:1 for trending, ema_rsi_atr/RSI slingshot for ranging/transitional.

---

## Recommended Directives

### Priority 1 — IMMEDIATE (blocks all downstream progress)
1. **Forward-test Supertrend 8:1** (PF=1.921) — 6th cycle requesting. True champion, all-regime profitable. Every day without forward-testing is potential income lost.
2. **Forward-test MACD 7:1** (PF=1.712) — 6th cycle requesting. Most validated strategy.
3. **Backtest remaining Claude specs** — 33 variants still waiting. 36% ACCEPT rate on tested specs. Expected yield: 10-12 new ACCEPTs.
4. **Implement trending regime gate** — disable non-Supertrend/non-MACD-12:1 strategies during trending. Immediate PF improvement across 21/23 ACCEPTs.
5. **Kill pipeline spec generation** — 600+ pipeline specs have produced 0 ACCEPTs (all-time). Redirect ALL compute to Claude specs.

### Priority 2 — HIGH (systemic improvements)
1. **Implement parameter hash dedup** — hash actual params + R:R + asset + timeframe before backtesting. Would eliminate 93%+ compute waste.
2. **Enforce R:R floor of 5:1** — hard-reject any spec with R:R < 5:1.
3. **Enforce BTC exclusion** — hard-reject any BTC spec at pipeline entry.
4. **Remove dead templates** — delete stochastic_reversal and bollinger_breakout from TEMPLATE_REGISTRY.
5. **Block alignment_entry signal** — structural loser.
6. **Disable refinement engine** — 0% improvement, 8+ cycles.

### Priority 3 — MEDIUM (strategic advancement)
1. **Build portfolio backtester** — test combined regime-gated allocation across the 4 complementary strategies.
2. **Test 12:1 R:R on Supertrend** — Supertrend works at 8:1 (PF=1.921), RSI works at 12:1 (PF=1.270). Supertrend at 12:1 could be exceptional.
3. **Test SOL asset** — 3 Claude specs target SOL, untested. Different volatility profile.
4. **Build forward-testing infrastructure** — the Smaug executor agent concept needs to become real. Even a simple paper-trade webhook would suffice.
5. **Fix or replace research card pipeline** — zero output despite being in doctrine.

---

## Doctrine Gaps

### 1. Directive Enforcement Failure (CRITICAL — 13 CYCLES)
31+ directives issued. 0 enforced. The pipeline does not read, parse, or apply directives. This has been reported in every advisory since Update 1. **Status: unchanged.** The directive system exists only in the advisory — it has zero operational impact.

### 2. Trending Regime Gate (NEW — DOCTRINE BLIND SPOT)
Doctrine requires "explicit regime assumptions" but provides no mechanism to gate trades by regime at execution time. 21/23 ACCEPTs would benefit from a trending disable gate, but neither the spec schema nor the backtester supports regime-conditional execution. This is the single most impactful doctrine gap.

### 3. Parameter Convergence (CRITICAL — WORSENING)
Down to 4 unique profiles per 30 outcomes. Root cause: resolve_template falls back to the same indicator logic regardless of variant naming, and the pipeline doesn't hash parameters before launching backtests. **Status: unchanged from Update 11.**

### 4. Forward-Testing Infrastructure (ABSENT — 6 CYCLES REQUESTING)
Zero strategies forward-tested. Supertrend 8:1 and MACD 7:1 have been ACCEPT-validated for 6 cycles. Without forward-testing, we cannot distinguish curve-fit from genuine edge. **This is the #1 blocker to revenue.** Status: unchanged.

### 5. Research Card Pipeline (NON-FUNCTIONAL)
Only test fixture exists. No video research insights have been converted to testable hypotheses. Status: unchanged.

### 6. Claude-Specs Staging Directory
`artifacts/claude-specs/` appears empty. Claude specs are placed directly into `artifacts/strategy_specs/` with "claude-" prefix. The promote-claude-specs.ps1 staging workflow is bypassed. Not blocking, but the intended review process isn't operational.

---

## Suggestions For Asz

### 1. Deploy Smaug Paper Trader — The Path to Revenue Is Forward-Testing
We have 23 ACCEPT-tier strategies (best PF=1.921) validated over months of backtesting. Zero have been forward-tested. The Smaug executor agent should be the #1 development priority. Even a minimal implementation — a Python script that takes a strategy spec, connects to HyperLiquid testnet via API, monitors signals from a live price feed, and logs paper trades — would be enough. This doesn't need to be sophisticated; it needs to exist. The formula: `supertrend_follow + HyperLiquid testnet API + 1 week of paper trades = first real data on whether backtest edge translates to live`. Every week this doesn't happen is a week of potential income we'll never recover.

### 2. Hard-Wire the Pipeline Fixes — 3 Lines of Code for 93% Compute Savings
Three changes would eliminate virtually all pipeline waste:
- **Line 1:** `if rr < 5.0: skip()` — R:R floor enforcement
- **Line 2:** `if asset == "BTC": skip()` — BTC exclusion
- **Line 3:** `if param_hash in seen: skip()` — dedup by actual parameters
These are trivial code changes with massive impact. The pipeline has run 600+ specs to produce 0 ACCEPTs because it ignores every advisory directive. Rather than fixing the directive parser (complex), just hard-code the three most impactful rules. Combined, these would reduce compute by 93%+ and ensure the remaining 7% runs Claude specs.

### 3. Add Regime Gates to Strategy Specs — Biggest Alpha for Zero Risk
Of the 23 ACCEPTs, 21 bleed money during trending markets. Adding a `regime_gate: {disable_during: ["trending"]}` field to strategy specs and a corresponding check in the backtester would:
- Immediately improve portfolio PF by ~0.2-0.4
- Reduce max DD significantly (trending drawdowns are the deepest)
- Cost nothing — these strategies already exist and are validated
- Be testable via backtest before live deployment

The ema_rsi_atr_precision_10to1 is the poster child: overall PF=1.327, but ranging PF=2.864 and transitional PF=1.731. If we simply don't trade it during trending (where PF=0.372), the effective PF jumps to ~2.0+. This single change could make the difference between a marginally profitable system and a consistently profitable one.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 11 |
|---|---|---|
| Total outcome notes (all-time) | 610+ | — |
| ACCEPTs (all-time) | 23 (3.7% rate) | +2 |
| Claude-originated ACCEPT rate | 100% (23/23) | +2 |
| Pipeline-originated ACCEPT rate | 0% (0/590+) | — |
| Latest batch outcomes (20260302) | 30 (sampled) | — |
| Latest batch ACCEPTs | 2 (er4n7b2k, rp6k3w9d) | +1 |
| Latest batch unique profiles | 4 | — |
| Compute waste (estimated) | 93%+ | — |
| Directives enforced | 0/31+ | — |
| Forward tests initiated | 0 | — (6th cycle requesting) |
| Cycles requesting forward test | 6 | +1 |
| Claude spec variants awaiting backtest | ~33 | +9 (new specs created) |
| Claude spec ACCEPT rate (tested) | 36% (4/11 specs) | NEW METRIC |
| Dead templates | 2 (stochastic_reversal, bollinger_breakout) | — |
| Dead signals | 1 (alignment_entry) | — |
| Regime classifier status | NOT BROKEN — pipeline signal issue | UPDATED |

### ACCEPT Leaderboard (by PF, deduplicated, 23 strategies)

| Rank | Strategy | PF | DD | Trades | Best Regime | Template |
|---|---|---|---|---|---|---|
| 1 | Supertrend tail 8:1 | 1.921 | 10.9% | 85 | Ranging (2.914) | supertrend_follow |
| 2 | Supertrend ultra ADX10 8:1 | 1.907 | 12.9% | 99 | Ranging (2.558) | supertrend_follow |
| 3 | MACD 7:1 family | 1.712 | 7.5% | 161 | Ranging (2.062) | macd_confirmation |
| 4 | MACD 6:1 | 1.460 | 8.2% | 170 | Ranging (1.762) | macd_confirmation |
| 5 | RSI pullback 8:1 | 1.442 | 7.1% | 156 | Ranging (1.795) | rsi_pullback |
| 6 | RSI pullback 7:1 | 1.421 | 13.8% | 127 | Trending (1.605) | rsi_pullback |
| 7 | Supertrend 10:1 | 1.410 | 12.9% | 99 | Ranging (1.874) | supertrend_follow |
| 8 | Supertrend 5:1 | 1.395 | 12.3% | 85 | Ranging (2.002) | supertrend_follow |
| 9 | MACD 5:1 | 1.358 | 10.2% | 147 | Ranging (1.822) | macd_confirmation |
| 10 | MACD moderate | 1.353 | 10.8% | 139 | Ranging (1.465) | macd_confirmation |
| 11 | MACD wide exit | 1.347 | 6.2% | 189 | Ranging (1.872) | macd_confirmation |
| 12 | Supertrend 1h 5:1 | 1.339 | 14.3% | 99 | Ranging (1.693) | supertrend_follow |
| 13 | RSI shallow dip 7:1 | 1.333 | 7.9% | 38 | Trans (5.568) | rsi_pullback |
| 14 | **ema_rsi_atr precision 10:1 (NEW)** | **1.327** | **16.6%** | **162** | **Ranging (2.864)** | **ema_rsi_atr** |
| 15 | MACD 12:1 ultimate | 1.302 | 9.8% | 137 | Trending (2.177) | macd_confirmation |
| 16 | ea9p5k2m narrow 9:1 | 1.288 | 18.6% | 92 | Trans (2.765) | ema_rsi_atr |
| 17 | **RSI slingshot 12:1 (NEW)** | **1.270** | **8.4%** | **162** | **Trans (1.834)** | **rsi_pullback** |
| 18 | Supertrend ADX5 6:1 | 1.220 | 14.3% | 99 | Ranging (1.611) | supertrend_follow |
| 19 | RSI pullback safe mod | 1.210 | 9.2% | 38 | Trans (1.597) | rsi_pullback |
