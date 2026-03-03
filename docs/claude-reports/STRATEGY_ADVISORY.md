# Strategy Advisory — 2026-03-04 (Update 21)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** ~770 outcome notes (latest 30), 54+ backtests, 18 brain objects, 10 research cards, 59+ batch runs, 3 pending Claude specs
**Prior advisory:** 2026-03-04 (Update 20)

---

## Machine Directives

```json
[
  {"action": "BLACKLIST_TEMPLATE", "target": "stochastic_reversal", "reason": "Bug confirmed: line 174 asymmetric k_prev/k_now. 0 trades, 18+ cycles."},
  {"action": "BLACKLIST_TEMPLATE", "target": "bollinger_breakout", "reason": "Volume gate structurally broken. 0 trades, 14+ cycles."},
  {"action": "BLACKLIST_SIGNAL", "target": "alignment_entry", "reason": "PF 0.615-0.969 across 6 backtests, structural loser."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "WILLR + STIFFNESS", "reason": "DEAD: 0 trades across 12 backtests."},
  {"action": "BLACKLIST_INDICATOR", "target": "STIFFNESS_20_3_100", "reason": "0 trades in every strategy. Dead."},
  {"action": "BLACKLIST_INDICATOR", "target": "QQE_14_5_4.236", "reason": "QQE Chop Fade PF=0.116."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "21 cycles. 0 BTC ACCEPTs across 770+ outcomes."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 15m ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "ALL ACCEPT-tier results are 4h."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "GATE_ADJUST", "reason": "0% success in 60+ applications."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_TIGHTEN", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "ENTRY_RELAX", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "THRESHOLD_SWEEP", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "EXIT_CHANGE", "reason": "0% success."},
  {"action": "BLACKLIST_DIRECTIVE", "target": "PARAM_SWEEP", "reason": "Produces identical metrics."},
  {"action": "BLACKLIST_VARIANT", "target": "directive_exploration", "reason": "PF 0.64-0.88, DD up to 1501%."},
  {"action": "PREFER_TEMPLATE", "target": "vortex_transition", "priority": 0, "reason": "CHAMPION: v3a PF=2.034. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "kama_stoch_pullback", "priority": 1, "reason": "ACCEPT: v1 PF=1.857. Forward-test candidate."},
  {"action": "PREFER_TEMPLATE", "target": "supertrend_follow", "priority": 2, "reason": "PF=1.921. Forward-testing."},
  {"action": "PREFER_TEMPLATE", "target": "macd_confirmation", "priority": 3, "reason": "9 ACCEPTs, best PF=1.712."},
  {"action": "STOP_FLOOR", "target": "stop_atr_mult", "minimum": 1.5},
  {"action": "RR_FLOOR", "target": "reward_risk_ratio", "minimum": 5.0},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate. 44 directive stall cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of ACCEPTs. Pipeline produces 0."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a_eth_4h", "reason": "LIVE."},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "reason": "LIVE."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1_eth_4h", "reason": "Third lane."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-almamh01", "reason": "ALMA+MACDh first test. Untested indicator."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-ichtk01v", "reason": "Ichimoku TK first test. Untested indicator."},
  {"action": "EXECUTE_PENDING_SPECS", "target": "strategy-spec-20260304-claude-t3vxpb01", "reason": "T3+Vortex Pullback first test. Untested indicator."},
  {"action": "PREFER_ADAPTIVE_INDICATORS", "reason": "Adaptive indicators (KAMA, Vortex) produce all-regime ACCEPTs."},
  {"action": "FLAG_ZERO_TRADE_EPIDEMIC", "affected_runs": 10, "reason": "ALL 10 recent backtests produced 0 trades. Signal conditions never co-fire."},
  {"action": "FLAG_DEDUP_SATURATION", "dedup_rate": "87%+", "reason": "Pipeline recycling known failures. No novel specs generated."},
  {"action": "FLAG_PIPELINE_STARVATION", "drought_cycles": 53, "directive_stall_cycles": 44, "reason": "Pipeline structurally dead. Post-BALROG-fix: runs but produces 0 trades."},
  {"action": "DESIGN_NEW_SPEC", "target": "kama_cci_pullback_8to1", "reason": "Extends KAMA architecture with CCI oscillator."},
  {"action": "DESIGN_NEW_SPEC", "target": "t3_ema_histogram_cross_8to1", "reason": "T3 vs EMA_21 crossover. Research-derived from TREX concept."},
  {"action": "INDICATOR_REQUEST", "target": "ehlers_hann_oscillator", "reason": "Cycle-based adaptive oscillator. Research-derived from TASC Directional Movement video."},
  {"action": "INDICATOR_REQUEST", "target": "regression_slope", "reason": "Multiple linear regression averaged trend signal. Research-derived."}
]
```

---

## Executive Summary

Zero new ACCEPTs. The BALROG YAML fix from U20 is **verified working** — backtests now execute without schema failures. However, the bottleneck has shifted: ALL 10 recent backtests produced **zero trades**. The systemic problem is no longer infrastructure but **signal generation** — pipeline-created entry conditions (AND-chains of 3-5 indicators) never simultaneously fire within the same bar.

Batch deduplication has reached saturation: 87%+ of runs are skipped (previously-tested parameter combinations). The pipeline is recycling failure, not exploring new territory. 27-run full-grid batches are 100% deduplicated.

Three Claude-specified strategies (ALMA MACDh, Ichimoku TK, T3 Vortex Pullback) remain **pending execution** — these are the only viable path to new ACCEPTs. Two new Claude spec designs are proposed this cycle: KAMA CCI Pullback 8:1 and T3 EMA Histogram Cross 8:1.

New research cards introduce actionable concepts: Ehlers Hann-function cycle detection, regression slope oscillators, TREX triple-exponential histogram, and dual EMA channel setups. Ehlers and regression slope require new indicator columns.

Forward-testing: 2 lanes active (Vortex v3a, Supertrend 8:1), 0 trades in ranging regime. Expected behavior. Graduation criteria remain undefined.

**Brain state**: 18 → 19 objects (+1 new fact: zero-trade signal bottleneck). All objects validated clean.

---

## Failing Patterns

### 1. Zero-Trade Epidemic (NEW — Critical)
All 10 recent backtests produced exactly 0 trades. This is systemic, not random:
- Pipeline-generated specs create AND-chains of 3-5 conditions that never align within the same bar
- Signal clustering detected on 1h (conditions fire on adjacent bars but never simultaneously)
- Pipeline continues targeting BTC 1h despite EXCLUDE directives
- Feasibility checks flag SIGNAL_CLUSTERED but pipeline doesn't respond

**Root cause**: Pipeline lacks hypothesis-driven signal design. Conditions are combinatorially assembled without understanding *why* they should co-occur.

### 2. Batch Deduplication Saturation (NEW)
- 27-run full-grid batches: **100% deduplicated** (0 new tests)
- 9-run batches: 100% deduplicated or directive-blocked
- Pipeline has exhausted its parameter space on known templates
- No mechanism to generate genuinely novel specs

### 3. Pipeline Deep Starvation (Persistent — Worsening)
- Drought cycles: **53** (unchanged from U20, but verified post-BALROG-fix)
- Directive stall cycles: **44**
- Post-fix status: pipeline runs but produces 0-trade results
- All refinement variants (ENTRY_TIGHTEN, PARAM_SWEEP, etc.) have 0% improvement rate
- 0/49 machine directives read or applied

### 4. Research Card Quality Still Low
- 8/10 latest TradingView catalog cards contain only title + author
- Only 2 cards (TREX Histogram, TASC Directional Movement) produced actionable rule sets
- Research pipeline producing volume but not quality

---

## Promising Directions

### Tier 1: Immediate (Existing Indicators, Pending Execution)
1. **ALMA MACDh Momentum** — First Gaussian-smoothed MA test. ALMA_9_6.0_0.85 reduces noise differently than EMA/KAMA. MACDh confirmation avoids false triggers.
2. **Ichimoku TK Cross + CCI** — First structural MA test. Ichimoku cloud provides regime context (above/below cloud). TK cross = momentum shift. Tests whether transition-detection is a general mechanism, not Vortex-specific.
3. **T3 Vortex Pullback** — First triple-smoothed MA test. T3_10_0.7 is the smoothest available MA. Combined with Vortex for transition detection.

### Tier 2: Next Cycle (Existing Indicators, New Designs)
4. **KAMA CCI Pullback 8:1** — KAMA_10_2_30 trend + CCI_20 oversold/overbought pullback. Extends the proven KAMA architecture (KAMA Stoch v1 PF=1.857) with a different oscillator. CCI has shown independent alpha (CCI Chop Fade v2 PF=1.255).
5. **T3 EMA Histogram Cross 8:1** — T3_10_0.7 crosses EMA_21 as a smoothed crossover signal. Research-derived from TREX triple-exponential histogram concept. CHOP < 50 ranging gate. Testable with existing indicators.
6. **KAMA Vortex Divergence** — Template exists (`kama_vortex_divergence`) but remains untested. Combines the two proven adaptive families.

### Tier 3: Future (Requires New Indicators)
7. **Ehlers Hann-Function Oscillator** — John Ehlers' Hann-windowed cycle detection. Inherently adaptive (adjusts to dominant cycle period). Research-derived from TASC Directional Movement video.
8. **Regression Slope Oscillator** — Multiple linear regression averaging for trend strength. Reduces whipsaws through averaging. Research-derived.
9. **Dual-MACD System** — Fast MACD(34/144/9) + Slow MACD(100/200/50). Research-derived from Red K Pressure Index video. Requires non-standard MACD parameter columns.

### Research Card Highlights (Actionable This Cycle)
From the latest 10 research cards, concepts that map to existing indicators:
- **TREX Histogram**: Triple-exponential smoothing → maps to T3_10_0.7 (already computed). Histogram crossover testable as T3 vs EMA crossover.
- **TASC Directional Movement**: Hann-function oscillator → NOT computed, requires new indicator. But Vortex (VTXP/VTXM) provides similar directional detection with existing columns.
- **Regression Slope**: Linear regression averaging → NOT computed. Novel approach.
- **Dual EMA Channel**: EMA 8 H/L + EMA 88 H/L → requires EMA on high/low prices (not currently computed).
- **Red K Pressure Index**: Bull/bear pressure quantification → NOT computed.

---

## Template Health

| Template | ACCEPTs | Best PF | Status |
|---|---|---|---|
| spec_rules (Claude) | 8 | 2.034 | **ACTIVE** — Only productive path |
| vortex_transition | 6 | 2.034 | CHAMPION (FORWARD-TESTING) |
| supertrend_follow | 7 | 1.921 | STRONG (FORWARD-TESTING) |
| macd_confirmation | 9 | 1.712 | STRONG (SATURATED) |
| kama_stoch_pullback | 1 | 1.857 | ACCEPT (FWD-TEST CANDIDATE) |
| rsi_pullback | 5 | 1.442 | GOOD (SATURATED) |
| cci_chop_fade | 1 | 1.255 | RISING |
| ema_rsi_atr | 2 | 1.327 | GOOD |
| alma_macdh (NEW) | 0 | — | PENDING BACKTEST |
| ichimoku_tk (NEW) | 0 | — | PENDING BACKTEST |
| t3_vortex_pullback (NEW) | 0 | — | PENDING BACKTEST |
| kama_vortex_divergence | 0 | — | **UNTESTED** |
| choppiness_donchian_fade | 0 | — | DEAD (gate too restrictive) |
| stc_cycle_timing | 0 | — | DEAD (transitional-only) |
| ema_crossover | 0 | — | EXHAUSTED |
| spec_rules (pipeline) | ~1 | 1.419 | DEAD (0 new in 53 cycles) |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## Regime Insights

- **Current market (forward-test):** ETH sustained ranging. Both live lanes correctly idle (Vortex waits for crossover, Supertrend waits for direction flip).
- **Ranging = universal base (conf 0.93):** All 8 ACCEPTs profitable in ranging (PF 1.12-4.87). Ranging transfers across assets (ETH and SOL both profitable).
- **Transitional = highest alpha (conf 0.88):** Vortex v3a trans PF=3.886 (system record). Only Vortex family consistently captures transitional alpha. Non-Vortex strategies typically lose in transitional (MACD trans PF=0.569).
- **Trending = danger zone (conf 0.88):** 21/24 legacy strategies lose during trending. Only adaptive strategies (Vortex, KAMA) survive. CHOP > 50 gate required for all non-adaptive strategies.
- **Key test pending:** Ichimoku TK targets transition detection via different mechanism than Vortex. If it works, transition-detection is a general edge, not indicator-specific.

---

## Recommended Directives

**Priority 0:** Execute the 3 pending Claude specs (ALMA MACDh, Ichimoku TK, T3 Vortex) on ETH 4h. This is the single highest-ROI action — ~22% ACCEPT probability each.

**Priority 1:** Design and queue 2 new Claude specs:
- KAMA CCI Pullback 8:1 (extends proven KAMA architecture)
- T3 EMA Histogram Cross 8:1 (research-derived, tests T3 as signal generator)

**Priority 2:** Promote KAMA Stoch v1 to third forward-test lane. Define forward-test graduation criteria (min 10 trades, min PF 1.2, min 30 days, 2+ regime types).

**Priority 3:** Pipeline triage decision — options:
- (A) Disable autonomous pipeline, redirect compute to Claude-specified backtests only
- (B) Repurpose pipeline for parameter sweeping on Claude-designed specs
- (C) Rebuild spec-generation with hypothesis-driven architecture

**Priority 4:** Request new indicators: Ehlers Hann oscillator, regression slope. Both are inherently adaptive, aligning with the brain's top design principle.

**Priority 5:** Fix TV catalog extraction (80% empty research cards). Consider dual-MACD spec (100/200/50 + 34/144/9) pending new indicator columns.

---

## Doctrine Gaps

1. **Forward-test graduation criteria** — Undefined. Strategies forward-test indefinitely with no promotion or demotion path. Recommended: min 10 trades, PF > 1.2 after fees, 30+ days, 2+ regime types traded.

2. **Research-to-spec pipeline** — No systematic process to convert research card concepts into testable strategy specs. Research cards accumulate but rarely translate to backtests.

3. **Directive enforcement** — 0/49 directives applied by pipeline. Directives are write-only documentation. No mechanism for the pipeline to read or act on them.

4. **Portfolio correlation analysis** — All 8 ACCEPTs are ETH 4h. No analysis of entry signal correlation between strategies. The roster may have concentrated exposure to the same market conditions.

5. **Signal feasibility pre-check** — Pipeline doesn't verify that entry conditions CAN co-occur at the target frequency before submitting to backtest. A simple correlation check on indicator values could prevent 0-trade runs.

6. **Indicator coverage tracking** — No systematic record of which indicators have been tested vs untested. Known untested: VWAP_D (in strategies), OBV (in strategies), ALMA (pending), ISA/ISB/ITS/IKS (pending), T3 (pending).

---

## Suggestions For Asz

1. **Execute the 3 pending Claude specs** — Highest ROI action. Each has ~22% chance of ACCEPT. ALMA, Ichimoku, and T3 are all untested indicator families that could diversify the portfolio.

2. **Define forward-test graduation criteria** — Vortex v3a and Supertrend 8:1 are running with no exit condition. Proposal: graduate after 10+ trades with PF > 1.2, demote if PF < 0.8 after 20 trades.

3. **Pipeline decision needed** — 53 drought cycles. 100% dedup on full-grid batches. Post-BALROG-fix the pipeline runs but produces 0-trade specs. Consider repurposing for parameter sweeping on Claude specs instead of autonomous generation.

4. **Add Ehlers Hann oscillator** — John Ehlers' cycle-based indicators are inherently adaptive and would extend the adaptive indicator family (currently: KAMA, Vortex, T3, ALMA). Research video provided specific implementation details.

5. **Fix TV catalog extraction** — 8/10 research cards empty. The video ingestion pipeline is producing metadata shells, not actionable indicator logic.

6. **Promote KAMA Stoch v1 to forward-test** — Third lane. PF=1.857, all-regime, ranging PF=4.87. Decorrelated from Vortex/Supertrend (uses KAMA adaptive speed + Stochastic oscillator vs directional movement).

---

## ACCEPT Leaderboard (top 12, unchanged)

| Rank | Strategy | PF | DD | Trades | All-Regime | Status |
|------|----------|----|----|--------|------------|--------|
| 1 | Vortex v3a 4h (ETH) | 2.034 | 15.2% | 84 | YES (trans 3.886) | FORWARD-TEST |
| 2 | Supertrend 8:1 (ETH) | 1.921 | 10.9% | 85 | YES (ranging 2.914) | FORWARD-TEST |
| 3 | Supertrend ultra ADX10 8:1 (ETH) | 1.907 | 12.9% | 99 | YES (ranging 2.558) | ACCEPT |
| 4 | Vortex v2c 4h (ETH) | 1.892 | 12.3% | 84 | YES (trans 2.986) | ACCEPT |
| 5 | Vortex v3b 4h (ETH) | 1.885 | 11.8% | 84 | YES (trans 2.250) | ACCEPT |
| 6 | KAMA Stoch v1 8:1 (ETH) | 1.857 | 10.1% | 42 | YES (ranging 4.87) | FWD-TEST CANDIDATE |
| 7 | Vortex v2a 4h (ETH) | 1.735 | 11.4% | 80 | — | ACCEPT |
| 8 | MACD 7:1 (ETH) | 1.712 | 7.5% | 161 | — | ACCEPT |
| 9 | MACD 6:1 (ETH) | 1.460 | 8.2% | 170 | — | ACCEPT |
| 10 | RSI pullback 8:1 (ETH) | 1.442 | 7.1% | 156 | — | ACCEPT |
| 11 | Pipeline template_div (ETH) | 1.419 | 10.5% | 140 | — | ACCEPT |
| 12 | CCI Chop Fade v2 4h (ETH) | 1.255 | 16.4% | 179 | YES | ACCEPT |

---

## Proposed New Spec Designs

### KAMA CCI Pullback 8:1

**Hypothesis:** KAMA's adaptive speed provides trend context. CCI oversold/overbought crossback provides pullback entry timing. Combines two proven-independent signal families (KAMA Stoch v1 PF=1.857 + CCI Chop Fade PF=1.255).

```yaml
name: kama_cci_pullback_v1_8to1
template_name: spec_rules
entry_long:
  - "close > KAMA_10_2_30"
  - "CCI_20_0.015 crosses_above -100"
entry_short:
  - "close < KAMA_10_2_30"
  - "CCI_20_0.015 crosses_below 100"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12
  risk_per_trade_pct: 0.01
```

### T3 EMA Histogram Cross 8:1

**Hypothesis:** T3 (triple-smoothed EMA) crossing a standard EMA provides a low-noise crossover signal. Derived from TREX Histogram research concept. CHOP gate ensures signals fire during trending/transitional periods only.

```yaml
name: t3_ema_histogram_cross_v1_8to1
template_name: spec_rules
entry_long:
  - "T3_10_0.7 crosses_above EMA_21"
  - "CHOP_14_1_100 < 50"
entry_short:
  - "T3_10_0.7 crosses_below EMA_21"
  - "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12
  risk_per_trade_pct: 0.01
```

---

## Data Summary

- Total backtests: 54+ (10 new this cycle — all 0 trades)
- Forward-test lanes: 2 active + 1 candidate
- ACCEPT-tier results: 8 (unchanged)
- All-regime profitable: 6
- Best backtest PF: 2.034 (Vortex v3a)
- Best ranging PF: 4.87 (KAMA Stoch v1)
- Brain objects: 19 (18 prior + 1 new)
- Pipeline drought cycles: 53
- Directive stall cycles: 44
- Batch dedup rate: 87%+
- Claude spec ACCEPT rate: 22.2% (8/36)
- Directives enforced: 0/49
- Pending Claude specs: 3 (ALMA, Ichimoku, T3)
- Proposed new specs: 2 (KAMA CCI Pullback, T3 EMA Histogram Cross)
