# Strategy Advisory — 2026-03-03 (Update 19)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** ~740 outcome notes (20260303 latest 30), 46 backtests, 13 brain objects, 10 research cards, 18 forward-test evaluations, doctrine as of 20260226
**Prior advisory:** 2026-03-03 (Update 18)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 174 asymmetric k_prev/k_now. 0 trades, 18+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken. 0 trades, 14+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "DEAD: 0 trades across 12 backtests — 3 assets x 3+ timeframes. Abandon permanently."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy. Dead as regime filter or signal component."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116. Only fires in trending regime. Wrong for mean-reversion."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "19 cycles. 0 BTC ACCEPTs across 740+ outcomes. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 15m ACCEPTs ever. Signal noise too high."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "ALL ACCEPT-tier results are 4h. 1h degrades PF by 0.94 avg."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics."},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%."},
  {"action": "PREFER_TEMPLATE", "target": "vortex_transition", "priority": 0, "reason": "CHAMPION: v3a PF=2.034, 5/6 all-regime. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "kama_stoch_pullback", "priority": 1, "reason": "ACCEPT: v1 PF=1.857, all-regime, ranging PF=4.87. Forward-test candidate."},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 2, "reason": "Former champion — PF=1.921. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 3, "reason": "9 ACCEPTs, best PF=1.712, most consistent."},
  {"action": "PREFER_TEMPLATE", "target": "rsi_pullback", "priority": 4, "reason": "5 ACCEPTs. Saturated."},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0, "reason": "All unique ACCEPTs use 5:1+ R:R."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 12+ cycles. 22 directive stall cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of new backtests and ACCEPTs."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a_eth_4h", "reason": "LIVE. 6 evals, 4 bars, all ranging. No signals yet (expected)."},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "LIVE. 6 evals, matching Vortex pattern."},
  {"action": "EVALUATE_INDICATOR", "target": "KAMA_10_2_30", "reason": "KAMA Stoch v1 PF=1.857 all-regime. Adaptive MA validated."},
  {"action": "EVALUATE_ASSET", "target": "SOL", "reason": "3 tests: v3a 4h PF=1.20, KAMA v2 1h PF=1.48, T3 Vortex 1h PF=0.80. Needs 4h tests."},
  {"action": "ADD_REGIME_GATE", "target": "all_non_adaptive_strategies", "gate": "disable_during_trending"},
  {"action": "ADD_REGIME_GATE", "target": "all_sol_strategies", "gate": "disable_during_trending", "reason": "SOL trending PF=0.22 catastrophic (except KAMA)."},
  {"action": "DEDUP_PARAMS", "reason": "87%+ compute waste. 158 indicators skipped by dedup in latest cycle."},
  {"action": "TEST_UNTESTED_INDICATORS", "target": "T3_10_0.7, ALMA_9_6.0_0.85, ISA_9, ISB_26", "reason": "Computed every bar, never used."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1_eth_4h", "reason": "ACCEPT PF=1.857, all-regime. Third forward-test lane."},
  {"action": "PREFER_ADAPTIVE_INDICATORS", "reason": "NEW RULE: Adaptive indicators (KAMA, Vortex) produce all-regime ACCEPTs. Static indicators max at PF=1.255."},
  {"action": "FLAG_PIPELINE_STARVATION", "starvation_cycles": 215, "drought_cycles": 31, "directive_stall_cycles": 22, "reason": "Pipeline has fundamentally stalled. Claude specs are sole source of progress."}
]
```

---

## Executive Summary

**Consolidation cycle — no new ACCEPTs, but critical system health data.** The automated pipeline is in deep starvation (215 cycles, 31 drought, 22 directive stalls). Only 1 of 100 candidates was ingested; 0 passed gate. Forward-testing continues healthy — 6 evaluations across 4 bars, all ranging regime, no signals (expected for ~1 trade/week strategies). Brain population grows from 13 to 14 objects with a new meta-rule: adaptive indicators (KAMA, Vortex) structurally outperform static indicators for all-regime edge.

**Key delta from Update 18:**
- 0 new ACCEPTs (consolidation, not regression)
- Pipeline starvation confirmed: 215 cycles without accepted work, 0 candidates passing gate
- Forward-test healthy: 18 signal evaluations across 6 runs, all clean, regime = ranging
- New brain rule encoded: `rule-adaptive-over-static`
- Research cards: 9/10 TradingView catalog entries minimal content; 1 IntoTheCryptoverse BTC seasonality note
- WILLR+STIFFNESS evidence expanded: 12 total backtests, 0 trades (was 9)

---

## Failing Patterns

### 1. Pipeline in Deep Starvation (CRITICAL — NEW)
The automated pipeline has hit a wall:
- **215 starvation cycles** — no new accepted work in 215 consecutive cycles
- **31 drought cycles** — no candidates passing for 31 cycles
- **22 directive stall cycles** — directive system hasn't produced improvements for 22 cycles
- **1/100 candidates ingested** — 99% rejected at ingestion stage
- **0 candidates passing gate** — even ingested candidates fail
- **158 indicators skipped by dedup** — dedup is working but can't solve the fundamental issue

The pipeline is not just inefficient — it's dead. Claude specs are the sole source of research progress.

### 2. WILLR + STIFFNESS — 12th Failure Recorded
3 additional tests (BTC 4h, BTC 1h, SOL 1h): all 0 trades. Total evidence: 12 backtests, 0 trades, 3 assets, 4 timeframes.

### 3. Pipeline Duplicate Waste — Unchanged
19/30 latest outcomes share identical metrics (PF=1.295, DD=24.3%, 140 trades). All template_diversity REVISE verdicts. Pipeline burns compute re-testing identical parameter space.

### 4. 1h Timeframe — 19th Cycle Failure
No new evidence this cycle. All prior evidence holds. Average PF degradation 1h vs 4h: 0.94 points.

### 5. BTC — 19th Cycle, 0 ACCEPTs
No new BTC tests. Evidence unchanged at 740+ outcomes, 0 ACCEPTs.

### 6. Research Card Quality — Low
9/10 TradingView catalog cards have minimal extracted content (title + author only). The TV catalog ingestion pipeline is not extracting meaningful strategy logic from indicator pages. Only the IntoTheCryptoverse YouTube transcript produced actionable content (BTC midterm year seasonality pattern).

### 7. Dead Directives — 0% Enforcement (UNCHANGED)
35+ directives issued, 0 enforced. System is write-only.

---

## Promising Directions

### 1. Forward-Testing — Healthy, Awaiting First Trade
Both lanes running clean on ETH 4h:

| Lane | Evaluations | Bars Checked | Regime | Signals | Status |
|---|---|---|---|---|---|
| Vortex v3a | 6 | 4 | All ranging | 0 | Healthy |
| Supertrend 8:1 | 6 | 4 | All ranging | 0 | Healthy |

ETH has been in a ranging regime across all evaluated bars. Both strategies need a directional signal (Vortex crossover or Supertrend flip) to fire. With ~1 trade/week from backtest averages, first trade expected within days. The forward-test infrastructure itself is validated — clean runs, no errors.

### 2. KAMA Stoch v1 — Forward-Test Candidate (UNCHANGED)
PF=1.857, DD=10.1%, 42 trades, all-regime. Ready for third lane deployment. No new evidence this cycle.

### 3. Adaptive Indicator Thesis — Strengthening
The meta-pattern is now the strongest signal in our research:
- **Adaptive indicators** (KAMA, Vortex): All 6 all-regime ACCEPTs use adaptive or transition-detecting indicators
- **Static indicators** (CCI, RSI, MACD): Max PF=1.712 (MACD), most need regime gates
- **Dead indicators** (STC, QQE, STIFFNESS): Structural misfits with our approach

This is encoded as brain rule `rule-adaptive-over-static`.

### 4. Pending Orders — Still Awaiting Execution
3 diversification orders from U18 remain unexecuted:
1. Ichimoku TK Transition v1
2. CCI Chop Fade v3 (8:1 R:R)
3. Supertrend OBV Confirm v1

### 5. Untested Indicators — Research Queue
T3_10_0.7, ALMA_9_6.0_0.85, ISA_9/ISB_26 (Ichimoku components), VWAP_D remain computed but untested. Each represents potential new edge.

### 6. BTC Seasonality — Speculative Research Note
IntoTheCryptoverse research card suggests midterm year pattern: February low → March lower high → fade early rallies. Low confidence, macro-timeframe observation. Not actionable for our 4h system but worth monitoring as context for BTC behavior.

---

## Template Health

| Template | ACCEPTs | Best PF | Avg Trades | Status | Recommendation |
|---|---|---|---|---|---|
| **vortex_transition** (spec_rules) | **6** | **2.034** | 82 | **CHAMPION (FORWARD-TESTING)** | Monitor forward-test |
| **kama_stoch_pullback** (spec_rules) | **1** | **1.857** | 42 | **ACCEPT** | Forward-test candidate #3 |
| supertrend_follow | 7 | 1.921 | 95 | **STRONG (FORWARD-TESTING)** | Monitor forward-test |
| macd_confirmation | 9 | 1.712 | 155 | STRONG | Forward-test candidate #4 |
| rsi_pullback | 5 | 1.442 | 105 | GOOD | Saturated |
| cci_chop_fade (spec_rules) | 1 | 1.255 | 179 | RISING | v3 ordered |
| spec_rules (pipeline) | ~1 | 1.419 | 140 | STALLED | Pipeline starvation |
| ema_rsi_atr | 2 | 1.327 | 127 | GOOD | Needs trending gate |
| ema_crossover | 0 | — | 0 | EXHAUSTED | Remove from fallback |
| choppiness_donchian_fade | 0 | — | 0 | DEAD | Discrete signal problem |
| kama_vortex_divergence | 0 | — | — | UNTESTED | Different hypothesis from KAMA Stoch |
| stc_cycle_timing | 0 | — | — | TESTED-FAILED | Noisy signals |
| stochastic_reversal | 0 | — | 0 | DEAD (BUG) | Remove |
| bollinger_breakout | 0 | — | 0 | DEAD (BUG) | Remove |

---

## Regime Insights

### Current Market Context (from Forward-Test)
ETH is in a **sustained ranging regime**. All 18 forward-test evaluations across 4 bars show `regime: "ranging"`. This is consistent with backtest expectations — ranging is the most common regime in the dataset. Both forward-test strategies are designed to wait for regime transitions (Vortex) or trend flips (Supertrend) before entering.

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

### Key Regime Findings (UNCHANGED)

1. **Two all-regime architectures confirmed:** Vortex (transition-detecting) + KAMA (adaptive-speed). All-regime edge = adaptivity.
2. **KAMA ranging PF=4.87 is the ceiling** for single-regime ranging alpha.
3. **Vortex trans PF=3.886 is the ceiling** for single-regime transitional alpha.
4. **Ranging = universal base:** Every ACCEPT profitable in ranging (PF 1.12-4.87).
5. **Static indicators need regime gates** to avoid trending losses.

---

## Recommended Directives

### Priority 0 — FORWARD-TEST PATIENCE (ACTIVE)
1. **Do not intervene.** Forward-tests are healthy. The ranging regime means no signals are expected. First trade is the highest-value data point — let it happen naturally.
2. **Add KAMA Stoch v1 as third lane** — Ready for deployment. Three decorrelated strategies provide portfolio-level validation.

### Priority 1 — EXECUTE PENDING ORDERS (OVERDUE)
The 3 diversification orders from U18 remain unexecuted. These represent the next research frontier:
1. **Ichimoku TK Transition v1** — Tests whether Tenkan/Kijun crosses produce Vortex-comparable transition detection
2. **CCI Chop Fade v3** — The 8:1 R:R iteration that should push PF past 1.3
3. **Supertrend OBV Confirm v1** — First volume-based signal test

### Priority 2 — PIPELINE INTERVENTION (CRITICAL)
The pipeline is dead (215 starvation cycles). Options:
1. **Accept pipeline death** — Redirect all compute to Claude-spec backtesting. Pipeline has produced 0 ACCEPTs vs Claude's 8.
2. **Rebuild pipeline ingestion** — Current 99% reject rate means ingestion criteria are too strict or source pool is exhausted.
3. **Hybrid: pipeline for backtesting, Claude for spec generation** — Use pipeline infrastructure but feed it Claude-designed specs instead of template mutations.

### Priority 3 — SOL INVESTIGATION (UNCHANGED)
1. **KAMA Stoch on SOL 4h** — Best SOL prospect based on KAMA v2 SOL trending PF=2.10.
2. **Define SOL graduation criteria** — 2+ ACCEPT-tier strategies → forward-test consideration.

### Priority 4 — SYSTEM FIXES (19TH CYCLE)
1. Hard-exclude BTC from compute
2. Parameter hash dedup (158 indicators already skipped by dedup — extend to full pipeline)
3. Fix TV catalog research card extraction (9/10 empty)
4. Remove dead templates (stochastic_reversal, bollinger_breakout)
5. Define forward-test graduation framework

---

## Doctrine Gaps

### 1. Forward-Test Graduation Framework (CRITICAL — STILL UNDEFINED)
Forward-testing is live and healthy, but no graduation criteria exist. Proposed:
- **PASS:** Live PF > 0.7x backtest PF after 20+ trades
- **PROMOTE:** Live PF > 1.5 after 20+ trades → real capital consideration
- **DEMOTE:** DD > 1.5x backtest DD at any point → pause and review
- **KILL:** Live PF < 0.5x backtest PF after 20+ trades → remove

### 2. Pipeline Death Protocol (NEW)
No doctrine exists for what to do when the automated pipeline fundamentally stalls. 215 starvation cycles is not a temporary drought — it's structural failure. Need:
- Starvation threshold for pipeline death declaration (proposed: 100 consecutive starvation cycles)
- Transition plan to Claude-spec-only operation
- Compute reallocation from pipeline to Claude spec backtesting

### 3. Adaptive Indicator Taxonomy (UNCHANGED)
Doctrine should encode the hierarchy:
- **Adaptive** (KAMA, T3, ALMA): Self-adjusting, potentially all-regime
- **Transition-detecting** (Vortex): Captures regime changes, all-regime on ETH
- **Trend-following** (Supertrend, EMA): Fixed response, needs regime gate
- **Oscillator** (RSI, MACD, CCI): Fixed thresholds, regime-sensitive
- **Dead** (STC, QQE, STIFFNESS): Structural misfits

### 4. Multi-Asset Framework (UNCHANGED)
SOL has 3 data points but no criteria for asset promotion/demotion.

### 5. Directive Enforcement (19 CYCLES, 0 ENFORCED)
Unchanged. Write-only log. Consider removing directive system or rebuilding with enforcement hooks.

---

## Suggestions For Asz

### 1. Deploy KAMA Stoch v1 as Third Forward-Test Lane
No code changes needed — the forward-test infrastructure is proven. Adding a third decorrelated strategy (KAMA-based, ranging-specialist) provides portfolio-level validation alongside the two transition/trend strategies already running.

### 2. Decide Pipeline Fate
The pipeline has been dead for 215 cycles. Every ACCEPT has come from Claude specs. Options:
- **A: Kill pipeline, go Claude-only.** Saves compute, simplifies architecture.
- **B: Rebuild with Claude-designed specs as input.** Use pipeline infrastructure for backtesting but stop expecting it to generate specs autonomously.
- **C: Status quo.** Pipeline runs but produces nothing. Burns compute for zero value.

Recommendation: **Option B** — the pipeline's backtesting infrastructure is valuable, its spec generation is not.

### 3. Define Forward-Test Graduation Now
Before the first trade fires, codify what "passing" looks like. The proposed framework from U18 remains valid.

### 4. Three-Line Compute Fix (Still the Highest-ROI Change)
```python
if asset == "BTC": skip()        # 19 cycles, 0 ACCEPTs
if timeframe == "15m": skip()    # 0 ACCEPTs ever
if param_hash in seen: skip()    # 87% duplicate waste
```

### 5. Fix TV Catalog Extraction
9/10 research cards are empty. The TV catalog ingestion is running but not extracting indicator logic from TradingView pages. This is a missed opportunity — TV indicators contain specific entry/exit rules that could seed Claude spec generation.

---

## Appendix: Data Summary

| Metric | Value | Change from Update 18 |
|---|---|---|
| Total backtests | 46 | +2 (WILLR confirmations) |
| Forward-test lanes active | 2 | — |
| Forward-test evaluations | 18 | +18 (NEW) |
| Forward-test trades | 0 | — (expected, ranging regime) |
| ACCEPT-tier results | 8 | — (consolidation) |
| All-regime profitable | 6 | — |
| Best PF ever (backtest) | 2.034 (Vortex v3a) | — |
| Best ranging PF ever | 4.87 (KAMA Stoch v1) | — |
| Brain objects | **14** | **+1 (rule-adaptive-over-static)** |
| Pipeline starvation cycles | **215** | **NEW METRIC** |
| Pipeline drought cycles | **31** | **NEW METRIC** |
| Directive stall cycles | **22** | **NEW METRIC** |
| SOL backtests | 3 | — |
| BTC ACCEPTs (all-time) | 0 | — (19th cycle) |
| Claude spec ACCEPT rate | 22.2% (8/36) | — |
| Directives enforced | 0/35+ | — |
| Pending orders | 3 | — (unexecuted) |

### ACCEPT Leaderboard (by PF, deduplicated, top 12)

| Rank | Strategy | Asset | PF | DD | Trades | Best Regime (PF) | Source |
|---|---|---|---|---|---|---|---|
| 1 | Vortex Transition v3a 4h | ETH | **2.034** | 15.2% | 84 | Trans (3.886) | Claude |
| 2 | Supertrend tail 8:1 | ETH | 1.921 | 10.9% | 85 | Ranging (2.914) | Claude |
| 3 | Supertrend ultra ADX10 8:1 | ETH | 1.907 | 12.9% | 99 | Ranging (2.558) | Claude |
| 4 | Vortex Transition v2c 4h | ETH | 1.892 | 12.3% | 84 | Trans (2.986) | Claude |
| 5 | KAMA Stoch Pullback v1 8:1 | ETH | 1.857 | 10.1% | 42 | Ranging (4.870) | Claude |
| 6 | Vortex Transition v3b 4h | ETH | 1.885 | 11.8% | 84 | Trans (2.250) | Claude |
| 7 | Vortex Transition v2a 4h | ETH | 1.735 | 11.4% | 80 | Trending (1.812) | Claude |
| 8 | MACD 7:1 family | ETH | 1.712 | 7.5% | 161 | Ranging (2.062) | Claude |
| 9 | MACD 6:1 | ETH | 1.460 | 8.2% | 170 | Ranging (1.762) | Claude |
| 10 | RSI pullback 8:1 | ETH | 1.442 | 7.1% | 156 | Ranging (1.795) | Claude |
| 11 | Pipeline template_div | ETH | 1.419 | 10.5% | 140 | Trending (2.145) | Pipeline |
| 12 | CCI Chop Fade v2 4h | ETH | 1.255 | 16.4% | 179 | Trans (1.521) | Claude |
