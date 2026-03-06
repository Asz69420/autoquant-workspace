# Strategy Advisory — 2026-03-06 (Update 35)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** No new backtest data since U33. 20+ more zero-trade directive outcomes (pipeline waste continues). 2 new research cards (HMM regime detection). Deeper regime analysis of U33 results reveals R:R tradeoff is architecture-dependent. **0 NEW ACCEPTs.** Total unique ACCEPTs: 11 (unchanged).
**Prior advisory:** 2026-03-06 (Update 34)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: asymmetric k_prev/k_now. 0 trades, 18+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken. 0 trades, 14+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "DEAD: 0 trades across 12 backtests."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy. Dead."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "Ichimoku + KAMA", "reason": "4 configs tested, best PF=1.090. Incompatible time horizons."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "CCI + T3 zero-cross", "reason": "PF=0.606 on ETH 1h. T3 too slow as CCI smoothing filter."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "OBV confirmation", "reason": "OBV trends with price, triples trades, halves PF. Use divergence only."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 930+ outcomes across 35 cycles."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 11 ACCEPTs are 4h."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "MAINTAINED: 300+ zero-trade backtests since kill order. Pipeline fully self-regenerating with no circuit-breaker."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "300+ zero-trade backtests since kill order. No circuit-breaker exists."},
  {"action": "HALT_SPEC_GENERATION", "reason": "MAINTAINED: All non-Claude generation must be stopped."},
  {"action": "REJECT_PIPELINE_PROMOTIONS", "targets": "artifacts/promotions/20260306/*.promotion_run.json", "reason": "All promotions from dead pipeline."},
  {"action": "DRAIN_BACKTEST_QUEUE", "reason": "MAINTAINED: 15 Claude specs blocked 3-5 cycles. Directive waste consumes all queue slots."},
  {"action": "QUEUE_PRIORITY_SYSTEM", "reason": "MAINTAINED: Claude specs must execute before directive pipeline specs."},
  {"action": "CLOSE_EMA200_FAMILY", "reason": "CONFIRMED U35: 7 variants tested (v2 12:1, v3 tight, v3 8:1, v3b 8:1, v3b 10:1). ALL DD>20%. Structurally incompatible with DD constraint."},
  {"action": "CLOSE_SUPERTREND_CCI_V4_VARIANTS", "reason": "NEW U35: 8:1 (DD=25.36%) and tight (DD=26.86%) both REJECT. Default 12:1 (DD=11.63%) confirmed as ONLY viable R:R for this architecture."},
  {"action": "TUNE_KAMA_VORTEX_DIV", "reason": "MAINTAINED: 9 trades, 0% WR. Needs template-level threshold widening before re-testing."},
  {"action": "QUEUE_REMAINING_CLAUDE_SPECS", "targets": ["12 flush specs (claude-ikucloud through claude-f3a8d5b1)", "claude-t3vtx01", "claude-mchtrn01", "claude-almcci01"], "reason": "15 specs blocked 3-5 cycles. Expected 3-4 ACCEPTs."},
  {"action": "REQUEST_INDICATOR", "target": "TRIX_14", "reason": "Transition-detection expansion. 12th cycle requesting."},
  {"action": "DEFINE_FWD_TEST_GRADUATION", "reason": "16th cycle requesting. Proposed: 30 days + PF>1.2 + DD<15%."},
  {"action": "ADD_FWD_TEST_CANDIDATES", "targets": ["KAMA Stoch v1", "Ichimoku TK v1", "Supertrend CCI v4"], "reason": "3 validated ACCEPTs awaiting forward-test enrollment."},
  {"action": "INVESTIGATE_HMM_REGIME", "reason": "NEW U35: Hidden Markov Model regime detection (Baum-Welch) = 6th framework validating transition-detection. Most mathematically rigorous of all 6."}
]
```

---

## Executive Summary

**Status: No new data since U33. Pipeline waste continues. HMM research adds 6th regime-detection framework. Deeper regime analysis reveals R:R optimization is architecture-dependent.**

1. **No new backtest results.** LAST_CYCLE_RESULTS unchanged since U33. 15 Claude specs (12 flush + 3 U33) remain blocked — 3 to 5 cycles depending on spec. The pipeline continues to self-regenerate: 20+ more zero-trade directive outcomes on 2026-03-06. The kill order has produced zero effect across 4 cycles.

2. **Deeper regime analysis of U33 data reveals R:R architecture dependence.** Supertrend CCI v4 8:1 (PF=1.358, DD=25.36%) vs default 12:1 (PF=1.290, DD=11.63%): the 8:1 R:R improved PF by 5% but DOUBLED DD. The 8:1 shifts alpha from ranging (1.989→1.548) to transitional (2.777→3.291) because narrower TP captures medium transitions but misses ranging profits. For confirmation-type strategies, wider TP is optimal — the opposite of transition-detection strategies. **The "8:1 sweet spot" rule is architecture-dependent.**

3. **EMA200 Vortex v3b results confirm family death.** v3b 8:1 and v3 8:1 produced IDENTICAL results (PF=1.046, DD=25.56%, 130 trades) — confirming these specs are the same. v3b 10:1 (PF=1.358, DD=32.20%) is the "best" remaining but still 60% over DD cap. Total: 7 test configurations, all DD>20%. No further EMA200 Vortex testing is warranted.

4. **HMM regime detection = 6th framework.** Two new research cards (Hidden Markov Model: Baum-Welch, Hidden Markov Reversal Finder) add probabilistic state-machine regime detection. Three regimes (Bull, Balance, Bear) with online Baum-Welch adaptation. This is the most mathematically rigorous of the 6 frameworks supporting transition-detection. Previous 5: Vortex (validated PF=2.034), Ichimoku TK (validated PF=1.604), SMC CHoCH/BOS (conceptual), VIX-VIXEQ (research), Euphoria (research).

---

## Failing Patterns

| Pattern | Evidence | Confidence | Status |
|---------|----------|------------|--------|
| Pipeline self-regeneration | 300+ zero-trade since kill, 20+ more today | 0.99 | CRITICAL — 4 cycles post-kill, no effect |
| Claude spec queue starvation | 15 specs, 0 results for 3-5 cycles | 0.99 | BLOCKING ALL PROGRESS |
| EMA200 + any config | 7 variants, ALL DD>20% (25-40%) | 0.97 | CLOSED — comprehensively dead |
| Supertrend CCI v4 variants | 8:1 DD=25.36%, tight DD=26.86% | 0.92 | CLOSED — default 12:1 only viable |
| BTC all strategies | 0 ACCEPTs in 930+ outcomes | 0.95 | EXCLUDE confirmed |
| kama_vortex_div signal starvation | 9 trades on 5002 bars = 0.18% fire rate | 0.70 | NEEDS PARAMETER REDESIGN |
| 3+ AND conditions | 100% 0-trade rate | 0.99 | Rule: max 2 conditions |

---

## Promising Directions

### P0: Execute 15 Pending Claude Specs (CRITICAL BLOCKER)
- 12 flush specs (claude-ikucloud through claude-f3a8d5b1) blocked since U31 (5+ cycles)
- 3 U33 specs (T3 Vortex, MACDh CHOP, ALMA CCI) with 7 variants blocked since U33 (3 cycles)
- At historical 20% ACCEPT rate on 15 specs, expecting 3 new ACCEPTs
- Every blocked cycle compounds opportunity cost. This is the #1 priority.

### P1: HMM-Inspired Regime-Aware Entries
- Baum-Welch HMM classifies market into Bull/Balance/Bear with probabilistic confidence
- Design principle: use regime probability as a continuous gate (not binary)
- **Hypothesis:** Entry confidence should scale with regime transition probability
- Currently untestable — would require implementing HMM indicator or approximating with existing indicators
- Near-term proxy: combine multiple transition detectors (Vortex + Ichimoku) for regime confidence scoring

### P2: kama_vortex_div Parameter Redesign
- Current KAMA slope threshold (0.001 normalized) too restrictive — 0.18% fire rate
- **Approach A:** Widen threshold to 0.003-0.005 (3-5x looser)
- **Approach B:** Change detection from "slope near zero" to "slope magnitude decreasing" (deceleration, not flatness)
- Combines two proven indicator families — mechanism is sound, parameters are wrong

### P3: R:R Optimization Per Architecture
- **NEW finding:** 8:1 is NOT universally optimal
- Transition-detection strategies (Vortex): 8:1 sweet spot (proven by 6 ACCEPTs)
- Confirmation strategies (Supertrend CCI): wider TP (12:1) gives better risk-adjusted returns
- Mean-reversion (CCI Chop Fade): wider TP also better (12:1 ACCEPT at DD=16.4%)
- Future specs should match R:R to architecture type

### P4: Forward-Test Enrollment
- 3 ACCEPTs ready: KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4
- Graduation criteria still undefined (16th cycle requesting)

---

## Template Health

| Template | ACCEPTs | Best PF | Status | Notes |
|----------|---------|---------|--------|-------|
| spec_rules (Claude) | 11 | 2.034 | ACTIVE | Sole source of progress |
| supertrend_follow | 4 | 1.921 | ACTIVE | CCI confirmation variant proven, 8:1/tight variants CLOSED |
| kama_vortex_divergence | 0 | — | SIGNAL-STARVED | 9 trades, 0% WR. Template threshold too restrictive. |
| ema_crossover | 0 | — | EXHAUSTED | 10+ cycles |
| rsi_pullback | 1 | 1.442 | STALE | Only 8:1 variant works |
| macd_confirmation | 2 | 1.712 | STALE | Only tail harvester |
| choppiness_donchian_fade | 1 | 1.255 | STALE | CCI Chop Fade only |
| bollinger_breakout | 0 | — | DEAD | Bug: volume gate |
| stochastic_reversal | 0 | — | DEAD | Bug: asymmetric k |
| stc_cycle_timing | 0 | — | DEAD | STC structural misfit |
| ema_rsi_atr | 0 | — | DEAD | Compound gate |
| directive_baseline_retest | 0 | — | DEAD | 300+ 0-trade |

---

## Regime Insights

**U35 deeper regime analysis of Supertrend CCI v4 variants:**

| Variant | PF | DD% | Trend PF | Range PF | Trans PF | Verdict |
|---------|-----|-----|----------|----------|----------|---------|
| Default 12:1 | 1.290 | 11.63 | 0.562 | 1.989 | 2.777 | **ACCEPT** |
| 8:1 | 1.358 | 25.36 | 0.742 | 1.548 | 3.291 | REJECT (DD) |
| Tight 0.75/10:1 | 1.179 | 26.86 | 0.779 | 1.433 | 1.764 | REJECT (DD) |

**Key regime-level findings:**
- **Narrower TP shifts alpha from ranging to transitional.** 8:1 transitional PF=3.291 (+18%) but ranging PF=1.548 (-22%). Medium-sized transitional moves get captured by closer TP; ranging moves (smaller) don't reach even 8 ATR.
- **Wider TP is better for confirmation strategies.** Unlike transition-detection where 8:1 is optimal, confirmation strategies enter LATER in moves (after Supertrend flip + CCI agreement). They need more room to run because they've already missed the initial impulse.
- **This challenges the universal 8:1 sweet spot.** Rule-minimum-rr-5to1 still holds (5:1 minimum). But the OPTIMAL R:R depends on entry timing: early-entry strategies (transition-detection) → 8:1, late-entry strategies (confirmation) → 12:1.

**EMA200 Vortex regime data (7 variants, all dead):**

| Variant | PF | DD% | Trend PF | Range PF | Trans PF |
|---------|-----|-----|----------|----------|----------|
| v3b 8:1 | 1.046 | 25.56 | 0.417 | 1.505 | 1.476 |
| v3b 10:1 | 1.358 | 32.20 | 0.574 | 1.751 | 2.297 |
| v3 8:1 | 1.046 | 25.56 | 0.417 | 1.505 | 1.476 |

Even v3b 10:1 (PF=1.358, trans PF=2.297) carries catastrophic DD=32.20%. The EMA200 filter creates a structural problem: entries cluster where volatility is HIGHEST (around the EMA200 crossover). No stop width fixes this.

**Six regime-detection frameworks (convergence):**
1. Vortex crossover — PF=2.034 (VALIDATED)
2. Ichimoku TK cross — PF=1.604 (VALIDATED)
3. Smart Money Concepts (CHoCH/BOS) — conceptual alignment
4. VIX-VIXEQ Regime Detector — realized vs expected volatility
5. Euphoria Indicator — momentum exhaustion zones
6. **Hidden Markov Model (NEW U35)** — probabilistic 3-state regime classifier with online adaptation

**Three proven all-regime architectures** (unchanged):
1. Transition-detection (Vortex, Ichimoku TK) — optimal R:R 8:1
2. Speed-adaptation (KAMA) — optimal R:R 8:1
3. Trend-confirmation (Supertrend + CCI) — optimal R:R 12:1, ranging/transitional specialist

---

## Recommended Directives (Priority Order)

1. **DRAIN BACKTEST QUEUE** — 15 Claude specs blocked 3-5 cycles. This is the #1 blocker, every cycle costs ~3 potential ACCEPTs.
2. **Execute 15 pending Claude specs** — 12 flush (claude-ikucloud through claude-f3a8d5b1) + 3 U33 (T3 Vortex, MACDh CHOP, ALMA CCI). Expecting 3 ACCEPTs.
3. **Close Supertrend CCI v4 variant exploration** — Default 12:1 is the only viable R:R for this architecture. 8:1 and tight both REJECT.
4. **Tune kama_vortex_div in signal_templates.py** — Widen kama_slope_threshold from 0.001 to 0.003-0.005. Current threshold generates 0.18% fire rate.
5. **Add TRIX_14** — 12th cycle requesting. `pandas_ta.trix(close, length=14)`.
6. **Define forward-test graduation** — 16th cycle requesting. 3 ACCEPTs waiting.

---

## Doctrine Gaps

| # | Gap | Impact | Cycles Open |
|---|-----|--------|-------------|
| 1 | No pipeline circuit-breaker | 300+ zero-trade, kill ineffective 4 cycles | 9 |
| 2 | No backtest queue drain mechanism | 15 Claude specs blocked 3-5 cycles | 2 |
| 3 | No forward-test lifecycle | 3 ACCEPTs waiting for enrollment | 16 |
| 4 | No indicator request pipeline | TRIX_14 waiting 12 cycles | 12 |
| 5 | No R:R optimization protocol | Architecture-dependent R:R not encoded | NEW |
| 6 | No research card dedup | Identical recombine clones | 7 |
| 7 | No spec validity pre-check | Pseudo-params pass unchecked | 7 |
| 8 | No template parameter tuning protocol | kama_vortex_div at 9 trades, no tuning path | 3 |
| 9 | Stale doctrine heuristics | Confidence 0.68-0.78, no updates 12+ days | 12+ |
| 10 | No queue priority system | 300 zero-trade specs execute before 15 Claude variants | 2 |

---

## Suggestions For Asz

1. **URGENT: Drain the backtest queue and confirm Claude spec execution status.** 15 Claude specs have produced ZERO results for 3-5 cycles. Pipeline waste continues unabated. Nothing else matters until Claude specs execute. If the queue infrastructure can't be fixed, manually run the specs via `python scripts/backtester/run_backtest.py` for each Claude spec.

2. **Implement queue priority or manual spec routing.** The kill order has failed across 4 cycles. If automated pipeline kill is not possible, route Claude specs manually. The 15 blocked specs are worth ~3 ACCEPTs at historical rates.

3. **Tune kama_vortex_div threshold in signal_templates.py.** Change `kama_slope_threshold` default from 0.001 to 0.003 (line 251). This should 3-5x the trade count from 9 to 30-45, enabling proper edge evaluation.

4. **Add TRIX_14.** 12th cycle requesting. `pandas_ta.trix(close, length=14)`. Simple addition to indicator computation.

5. **Define forward-test graduation criteria.** 16th cycle requesting. Three ACCEPTs ready (KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4). Proposed: 30 days live, PF > 1.2, DD < 15%.

---

## Top 11 ACCEPTs (unchanged since U31)

| # | Strategy | PF | DD% | Trades | Regime Profile | Optimal R:R | Notes |
|---|----------|-----|-----|--------|----------------|-------------|-------|
| 1 | Vortex v3a 4h | 2.034 | 15.2 | 84 | All-regime (trans 3.886) | 8:1 | CHAMPION. FWD-TEST LIVE |
| 2 | EMA200 Vortex v2 12:1 | 1.969 | 30.0 | 52 | All-regime (trans 4.321 RECORD) | 12:1 | Conditional — DD. FAMILY CLOSED |
| 3 | Supertrend 8:1 | 1.921 | 10.9 | 85 | All-regime (ranging 2.914) | 8:1 | FWD-TEST LIVE |
| 4 | Supertrend ultra ADX10 | 1.907 | 12.9 | 99 | Ranging 2.558 | 8:1 | |
| 5 | Vortex v2c 4h | 1.892 | 12.3 | 84 | All-regime (trans 2.986) | 8:1 | |
| 6 | Vortex v3b 4h | 1.885 | 11.8 | 84 | All-regime (trans 2.250) | 8:1 | |
| 7 | KAMA Stoch v1 8:1 | 1.857 | 10.1 | 42 | All-regime (ranging 4.87) | 8:1 | FWD-TEST candidate |
| 8 | Vortex v2a 4h | 1.735 | 11.4 | 80 | | 8:1 | |
| 9 | MACD 7:1 | 1.712 | 7.5 | 161 | Ranging 2.06 | 7:1 | |
| 10 | Ichimoku TK v1 4h | 1.604 | 20.4 | 111 | All-regime | 8:1 | FWD-TEST candidate |
| 11 | Supertrend CCI v4 4h | 1.290 | 11.6 | 112 | Rang/trans specialist | **12:1** | FWD-TEST candidate. Variants CLOSED |
