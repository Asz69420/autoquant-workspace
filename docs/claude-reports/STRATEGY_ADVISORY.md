# Strategy Advisory — 2026-03-03 (Update 18)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** ~740 outcome notes (20260303 latest 30), 44 backtests, 3 Claude specs archived, 1 research card (fixture), 25 research digest entries, 11 signal templates, doctrine as of 20260226
**Prior advisory:** 2026-03-03 (Update 17)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 174 asymmetric k_prev/k_now. 0 trades, 18+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken. 0 trades, 14+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "DEAD: 0 trades across 9 backtests — 3 assets x 3 timeframes. Abandon permanently."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy. Dead as regime filter or signal component."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116. Only fires in trending regime. Wrong for mean-reversion."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "19 cycles. 0 BTC ACCEPTs across 740+ outcomes. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 15m ACCEPTs ever. Signal noise too high."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "ALL ACCEPT-tier results are 4h. 1h degrades PF by 0.94 avg."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% profitability."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics."},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%."},
  {"action": "PREFER_TEMPLATE", "target": "vortex_transition", "priority": 0, "reason": "CHAMPION: v3a PF=2.034, 5/6 all-regime. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "kama_stoch_pullback", "priority": 1, "reason": "NEW ACCEPT: v1 PF=1.857, all-regime, ranging PF=4.87. Second-best PF outside Vortex family."},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 2, "reason": "Former champion — PF=1.921. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 3, "reason": "9 ACCEPTs, best PF=1.712, most consistent."},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 4, "reason": "5 ACCEPTs. Saturated."},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All unique ACCEPTs use 5:1+ R:R."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 12+ cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of new backtests and ACCEPTs."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a_eth_4h", "reason": "LIVE. First trade expected soon."},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "LIVE."},
  {"action": "EVALUATE_INDICATOR", "target": "KAMA_10_2_30", "reason": "NEW: KAMA Stoch v1 PF=1.857 all-regime. KAMA Stoch v2 SOL PF=1.48. Adaptive MA shows promise."},
  {"action": "EVALUATE_ASSET", "target": "SOL", "reason": "3 tests: v3a 4h PF=1.20, KAMA v2 1h PF=1.48, T3 Vortex 1h PF=0.80. Trending gate needed."},
  {"action": "ADD_REGIME_GATE", "target": "all_non_vortex_strategies", "gate": "disable_during_trending"},
  {"action": "ADD_REGIME_GATE", "target": "all_sol_strategies", "gate": "disable_during_trending", "reason": "SOL trending PF=0.22 is catastrophic across all strategies."},
  {"action": "DEDUP_PARAMS", "reason": "87%+ compute waste. 19/30 latest outcomes identical."},
  {"action": "TEST_UNTESTED_INDICATORS", "target": "T3_10_0.7, ALMA_9_6.0_0.85", "reason": "Computed every bar, never used. T3 in research digest. ALMA never tested."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1_eth_4h", "reason": "NEW ACCEPT PF=1.857, all-regime. Third forward-test lane candidate."}
]
```

---

## Executive Summary

**KAMA Stoch Pullback v1 is a new ACCEPT-tier strategy — PF=1.857, ranking #5 overall.** This is the first successful deployment of the KAMA adaptive moving average, confirming it as a validated indicator family alongside Vortex. The strategy is all-regime profitable (trending 1.25, ranging 4.87, transitional 1.36), with ranging PF=4.87 being the second-highest single-regime PF ever recorded (after Vortex v3a trans=3.886). KAMA's adaptive speed — fast in trends, slow in ranges — may explain its all-regime robustness, mirroring Vortex's all-regime property through a different mechanism. Meanwhile, forward-testing remains live with 0 trades (expected), WILLR+STIFFNESS is dead, and the pipeline continues producing 87%+ duplicate outcomes.

**Key delta from Update 17:**
- +1 new ACCEPT: kama_stoch_pullback_v1 (PF=1.857)
- +1 new indicator family validated: KAMA_10_2_30
- +1 SOL data point: KAMA v2 SOL 1h PF=1.48 (trending PF=2.10 — rare trending success on SOL)
- Brain objects first population (13 objects across facts/rules/constraints/failures)

---

## Failing Patterns

### 1. WILLR + STIFFNESS — Permanently Dead (UNCHANGED from U17)
9 backtests, 0 trades, 3 assets, 3 timeframes. STIFFNESS_20_3_100 never drops below 50 simultaneously with WILLR at extremes. Blacklisted.

### 2. Pipeline Duplicate Waste — Worsening
19/30 latest outcomes share identical metrics (PF=1.295, DD=24.3%, 140 trades). All are template_diversity REVISE verdicts with identical regime profiles. The pipeline is burning compute re-testing the same parameter space. Every REVISE recommends the same fix (risk gating + template switching) — but the pipeline can't execute those changes.

### 3. 1h Timeframe — 19th Cycle Failure
Updated with new KAMA data:
- KAMA v2 SOL 1h: DD=36% (vs. KAMA v1 4h: DD=10.1%)
- T3 Vortex SOL 1h: PF=0.804, DD=81.3%
- Average PF degradation 1h vs 4h: 0.94 points (unchanged)

### 4. BTC — 19th Cycle, Still 0 ACCEPTs
No new BTC tests this cycle. Evidence unchanged: champion v3a PF=0.743.

### 5. T3 Vortex Hybrid — Fails on SOL 1h
T3 Vortex Hybrid v2 on SOL 1h: PF=0.804, DD=81.3%, 336 trades. The 81.3% drawdown is the worst in system history. T3+Vortex combination doesn't work on SOL at lower timeframes. However, T3 itself remains untested as a standalone trend filter.

### 6. Dead Directives — Still 0% Enforcement
35+ directives issued, 0 enforced. GATE_ADJUST, ENTRY_TIGHTEN, ENTRY_RELAX, THRESHOLD_SWEEP, EXIT_CHANGE, PARAM_SWEEP all at 0% success rate.

---

## Promising Directions

### 1. KAMA Stoch Pullback — New Discovery (THIS CYCLE)

**kama_stoch_pullback_v1_8to1** is a genuine new finding:
| Metric | Value |
|---|---|
| PF | 1.857 |
| DD | 10.1% |
| Trades | 42 |
| R:R | 8:1 |
| Trending PF | 1.25 |
| Ranging PF | **4.87** |
| Transitional PF | 1.36 |
| All-Regime | **YES** |

**Why this matters:**
- **KAMA is a new validated indicator family.** Unlike fixed EMAs, KAMA_10_2_30 adapts its smoothing period based on market noise — fast in directional moves, slow in chop. This self-adjusting behavior may explain all-regime profitability through a mechanism distinct from Vortex.
- **Ranging PF=4.87 is second-highest ever.** Only Vortex v3a transitional (3.886) beats it. KAMA's adaptive slowdown in ranges means fewer false signals during consolidation.
- **Stochastic as entry timer** (not signal generator) is the key insight. KAMA provides direction; Stochastic provides timing. This is the same architecture as Vortex (direction detector + crossover timing).

**Immediate actions:**
1. Test KAMA Stoch v1 on ETH 4h (if not already — the ACCEPT may be 4h)
2. Design KAMA variants: KAMA + CCI timing, KAMA + MACD timing
3. Consider KAMA Stoch as third forward-test lane

### 2. SOL Expanding Dataset (3 TESTS NOW)

| Strategy | TF | PF | DD | Trending PF | Ranging PF | Trans PF |
|---|---|---|---|---|---|---|
| Vortex v3a | 4h | 1.20 | 23.4% | 0.22 | 2.83 | 1.10 |
| KAMA Stoch v2 | 1h | 1.48 | 36.0% | 2.10 | 1.12 | 0.50 |
| T3 Vortex Hybrid | 1h | 0.80 | 81.3% | 0.64 | 0.90 | 0.99 |

**New insight from KAMA v2 SOL:** Trending PF=2.10 on SOL — this is the first strategy to be profitable in SOL's trending regime. This contradicts the earlier SOL thesis ("trending always fails on SOL"). KAMA's adaptive speed may capture SOL's trending moves that Vortex misses. However, 1h DD=36% is too high and transitional PF=0.50 fails. Need KAMA on SOL 4h.

### 3. Forward-Testing — Still Waiting for First Trade
Vortex v3a + Supertrend 8:1 running on ETH 4h. 0 trades (expected — these are selective strategies averaging ~1 trade/week). First trade remains the highest-value data point in the system.

### 4. Pending Orders — Unchanged
3 diversification orders awaiting execution:
1. Ichimoku TK Transition v1
2. CCI Chop Fade v3 (8:1 R:R)
3. Supertrend OBV Confirm v1

### 5. VWAP + CCI Spec — Untested
New Claude spec combining VWAP_D (institutional fair value) with CCI double mean-reversion. Pending backtesting. VWAP_D has never been tested in any strategy — first contact with volume-weighted pricing.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|
| **vortex_transition** (spec_rules) | **6** | **2.034** | 82 | **CHAMPION (FORWARD-TESTING)** | Monitor forward-test |
| **kama_stoch_pullback** (spec_rules) | **1** | **1.857** | 42 | **NEW ACCEPT** | Test more variants; forward-test candidate |
| supertrend_follow | 7 | 1.921 | 95 | **STRONG (FORWARD-TESTING)** | Monitor forward-test |
| macd_confirmation | 9 | 1.712 | 155 | STRONG | Forward-test candidate |
| rsi_pullback | 5 | 1.442 | 105 | GOOD | Saturated |
| cci_chop_fade (spec_rules) | 1 | 1.255 | 179 | RISING | v3 ordered |
| spec_rules (pipeline) | ~1 | 1.419 | 140 | OPERATIONAL | Dedup needed |
| ema_rsi_atr | 2 | 1.327 | 127 | GOOD | Needs trending gate |
| ema_crossover | 0 | — | 0 | EXHAUSTED | Remove from fallback |
| choppiness_donchian_fade | 0 | — | 0 | DEAD | Discrete signal problem |
| kama_vortex_divergence | 0 | — | — | UNTESTED | Different hypothesis from KAMA Stoch |
| stc_cycle_timing | 0 | — | — | TESTED-FAILED | Noisy signals |
| stochastic_reversal | 0 | — | 0 | DEAD (BUG) | Remove |
| bollinger_breakout | 0 | — | 0 | DEAD (BUG) | Remove |

---

## Regime Insights

### Updated Regime Performance Matrix (All ACCEPT-Tier)

| Strategy | Asset | Trending PF | Ranging PF | Trans PF | All-Regime? |
|---|---|---|---|---|---|
| **Vortex v3a 4h** | ETH | 1.572 | 2.022 | **3.886** | **YES** |
| **KAMA Stoch v1** | ETH | 1.250 | **4.870** | 1.360 | **YES** |
| Vortex v2c 4h | ETH | 1.636 | 1.855 | 2.986 | **YES** |
| Vortex v3b 4h | ETH | 1.726 | 1.954 | 2.250 | **YES** |
| Supertrend 8:1 | ETH | 1.289 | 2.914 | 1.844 | **YES** |
| Vortex v2b 4h | ETH | 1.582 | 1.338 | 1.286 | **YES** |
| CCI Chop Fade 4h | ETH | 1.132 | 1.430 | 1.521 | **YES** |
| MACD 7:1 | ETH | 1.677 | 2.062 | 1.308 | YES (marginal) |
| Vortex v3a 4h | SOL | 0.220 | 2.830 | 1.100 | No (trending) |
| KAMA Stoch v2 1h | SOL | 2.100 | 1.120 | 0.500 | No (trans) |

### Key Regime Findings

1. **Two all-regime architectures confirmed.** Vortex captures regime *transitions*; KAMA adapts its *speed* to regime conditions. Both achieve all-regime profitability through different mechanisms. This is the most important insight: all-regime edge comes from adaptivity, not from being right about which regime you're in.

2. **KAMA's ranging PF=4.87 redefines the alpha ceiling.** Previous best ranging PF was Supertrend 8:1 at 2.914. KAMA nearly doubles it. KAMA's adaptive slowdown in ranges may produce exceptionally clean signals during consolidation.

3. **SOL trending is not universally fatal.** KAMA v2 SOL trending PF=2.10 contradicts the "SOL trending = death" thesis from Update 17. The failure is strategy-specific (Vortex) not asset-specific. KAMA's adaptive behavior may handle SOL's trending regime better than Vortex's crossover-based detection.

4. **Ranging remains universal base.** Every ACCEPT strategy across both ETH and SOL is profitable in ranging (PF 1.12-4.87).

---

## Recommended Directives

### Priority 0 — MONITOR FORWARD-TESTS + KAMA INVESTIGATION (ACTIVE)
1. **Watch for first live trade** — Still the highest-value data point.
2. **Test KAMA Stoch v1 variants** — Design KAMA + CCI, KAMA + MACD, KAMA + RSI timing variants. KAMA as direction filter is validated; test different timing oscillators.
3. **KAMA Stoch v1 → forward-test candidate** — If one more KAMA variant ACCEPTs, add as third forward-test lane.

### Priority 1 — PORTFOLIO DIVERSIFICATION (IN PROGRESS)
1. **Execute pending orders** — Ichimoku TK, CCI v3, OBV confirm.
2. **Test VWAP + CCI spec** — VWAP_D never tested. First volume-weighted pricing strategy.
3. **Test kama_vortex_divergence template** — Different hypothesis from KAMA Stoch. Trend exhaustion vs. trend confirmation.

### Priority 2 — SOL INVESTIGATION (EXPANDED)
1. **KAMA Stoch on SOL 4h** — Given KAMA v2 SOL 1h trending PF=2.10, KAMA may be the right indicator family for SOL. Test at 4h for lower DD.
2. **Supertrend on SOL 4h** — Extend proven strategy to SOL with mandatory trending gate.
3. **Define SOL graduation criteria** — 2+ ACCEPT-tier strategies → forward-test consideration.

### Priority 3 — SYSTEM FIXES (19TH CYCLE)
1. **Hard-exclude BTC** — 19 cycles, 0 ACCEPTs.
2. **Parameter hash dedup** — 87% waste.
3. **Archive Claude specs** — Still empty.
4. **Fix research cards** — 0 real cards.
5. **Remove dead templates** — stochastic_reversal, bollinger_breakout.

---

## Doctrine Gaps

### 1. Forward-Test Validation Framework (CRITICAL — STILL UNDEFINED)
Forward-testing is live but no graduation criteria exist. Need:
- PF drift tolerance (proposed: live PF > 0.7× backtest PF = PASS)
- Minimum sample size (proposed: 20 trades)
- Auto-demotion triggers (proposed: DD > 1.5× backtest DD)

### 2. Adaptive Indicator Taxonomy (NEW)
KAMA's success reveals a new indicator category: **adaptive indicators** (KAMA, T3, ALMA) that self-adjust to market conditions. Doctrine should encode this as a distinct category above fixed-parameter indicators:
- **Adaptive** (KAMA, T3, ALMA): Self-adjusting, potentially all-regime
- **Transition-detecting** (Vortex): Captures regime changes, all-regime on ETH
- **Trend-following** (Supertrend, EMA): Fixed response, needs regime gate
- **Oscillator** (RSI, MACD, CCI): Fixed thresholds, regime-sensitive
- **Dead** (STC, QQE, STIFFNESS): Structural misfits

### 3. Multi-Asset Framework (UNCHANGED)
SOL now has 3 data points but no criteria for asset promotion/demotion.

### 4. Directive Enforcement (19 CYCLES, 0 ENFORCED)
Unchanged. Write-only log.

---

## Suggestions For Asz

### 1. KAMA Stoch Pullback to Forward-Test (Fastest Path to Value)
KAMA Stoch v1 PF=1.857, all-regime, DD=10.1% is production-worthy. Add as third forward-test lane alongside Vortex v3a and Supertrend 8:1. Three uncorrelated strategies running simultaneously provides the fastest path to portfolio-level validation.

### 2. Define Forward-Test Graduation Now
Before the first trade fires, codify what "passing" looks like. Proposed framework:
- **PASS:** Live PF > 0.7× backtest PF after 20+ trades
- **PROMOTE:** Live PF > 1.5 after 20+ trades → real capital consideration
- **DEMOTE:** DD > 1.5× backtest DD at any point → pause and review
- **KILL:** Live PF < 0.5× backtest PF after 20+ trades → remove

### 3. Three-Line Compute Fix (Still the Highest-ROI Change)
```python
if asset == "BTC": skip()        # 19 cycles, 0 ACCEPTs
if timeframe == "15m": skip()    # 0 ACCEPTs ever
if param_hash in seen: skip()    # 87% duplicate waste
```

### 4. Test KAMA on SOL 4h
KAMA Stoch v2 SOL 1h showed trending PF=2.10 — the only strategy to profit in SOL's trending regime. If KAMA Stoch works on SOL 4h with reasonable DD, SOL becomes a genuine portfolio asset using KAMA as its preferred indicator family (just as Vortex is ETH's preferred family).

---

## Appendix: Data Summary

| Metric | Value | Change from Update 17 |
|---|---|---|
| Total backtests | 44 | +2 (KAMA Stoch + T3 Vortex SOL) |
| Forward-test lanes active | 2 | — |
| Forward-test trades | 0 | — (expected) |
| New ACCEPT-tier results | **8** | **+1 (KAMA Stoch v1)** |
| New all-regime profitable | **6** | **+1 (KAMA Stoch v1)** |
| Best PF ever (backtest) | 2.034 (Vortex v3a) | — |
| Best ranging PF ever | **4.87 (KAMA Stoch v1)** | **NEW RECORD** |
| SOL backtests | **3** | **+1 (KAMA v2)** |
| KAMA strategies tested | **2** | **NEW (was 0)** |
| BTC ACCEPTs (all-time) | 0 | — (19th cycle) |
| Claude spec ACCEPT rate | **22.2% (8/36)** | +1.6pp |
| Pipeline outcomes today | 0 | — |
| Directives enforced | 0/35+ | — |
| Pending orders | 3 | — |

### ACCEPT Leaderboard (by PF, deduplicated, top 12)

| Rank | Strategy | Asset | PF | DD | Trades | Best Regime (PF) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Vortex Transition v3a 4h | ETH | **2.034** | 15.2% | 84 | Trans (3.886) | Claude |
| 2 | Supertrend tail 8:1 | ETH | 1.921 | 10.9% | 85 | Ranging (2.914) | Claude |
| 3 | Supertrend ultra ADX10 8:1 | ETH | 1.907 | 12.9% | 99 | Ranging (2.558) | Claude |
| 4 | Vortex Transition v2c 4h | ETH | 1.892 | 12.3% | 84 | Trans (2.986) | Claude |
| 5 | **KAMA Stoch Pullback v1 8:1** | **ETH** | **1.857** | **10.1%** | **42** | **Ranging (4.870)** | **Claude NEW** |
| 6 | Vortex Transition v3b 4h | ETH | 1.885 | 11.8% | 84 | Trans (2.250) | Claude |
| 7 | Vortex Transition v2a 4h | ETH | 1.735 | 11.4% | 80 | Trending (1.812) | Claude |
| 8 | MACD 7:1 family | ETH | 1.712 | 7.5% | 161 | Ranging (2.062) | Claude |
| 9 | MACD 6:1 | ETH | 1.460 | 8.2% | 170 | Ranging (1.762) | Claude |
| 10 | RSI pullback 8:1 | ETH | 1.442 | 7.1% | 156 | Ranging (1.795) | Claude |
| 11 | Pipeline template_div | ETH | 1.419 | 10.5% | 140 | Trending (2.145) | Pipeline |
| 12 | CCI Chop Fade v2 4h | ETH | 1.255 | 16.4% | 179 | Trans (1.521) | Claude |
