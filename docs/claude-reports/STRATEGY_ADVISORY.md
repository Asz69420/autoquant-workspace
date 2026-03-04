# Strategy Advisory — 2026-03-05 (Update 27)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 0 new backtests since U26, 3 new pipeline specs generated, 9 Claude specs blocked, 0 NEW ACCEPTs
**Prior advisory:** 2026-03-05 (Update 26)

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
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "Ichimoku + KAMA", "reason": "4 configs tested, best PF=1.090. Incompatible time horizons."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "CCI + T3 zero-cross", "reason": "PF=0.606 on ETH 1h. T3 too slow as CCI smoothing filter."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "OBV confirmation", "reason": "OBV trends with price, triples trades, halves PF. Use divergence only."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 27 cycles. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD accumulation prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles. Consuming backtest slots for zero output."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "CRITICAL U27: 9 Claude specs blocked 4+ cycles. 22% ACCEPT rate vs pipeline ~0%. 27+ variants ready to run."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "ESCALATED U27: 102+ consecutive 0-trade backtests. Pipeline still generating new specs despite total failure."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "ESCALATED U27: Pipeline generating specs faster than it can backtest them. Waste backlog growing."},
  {"action": "HALT_PIPELINE", "reason": "ESCALATED U27: Pipeline self-regenerating — 3 new specs + 2 promotions generated AFTER 102+ epidemic. Full halt, immediate."},
  {"action": "HALT_SPEC_GENERATION", "reason": "NEW U27: Pipeline generating new specs (489f8bcaea8f, 88cf9e406e3d, d7a7a5e46d09) that will produce more 0-trade runs. Stop generation, not just backtesting."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT. Spec EXISTS (claude-d4e1f8a3). BLOCKED 5 cycles."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop. Spec EXISTS (claude-b7c2a9e6). BLOCKED 4 cycles."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "TRIX triple-smoothed EMA. Transition-detection candidate via zero-cross. Requested since U24."},
  {"action": "INDICATOR_REQUEST", "target": "TREX_histogram", "reason": "Research card — triple exponentially smoothed MA histogram. Transition-detection via zero-cross."},
  {"action": "INDICATOR_REQUEST", "target": "TASC_DM_hilbert", "reason": "Research card — Hilbert transform directional movement. Mathematical phase detection for regime transitions."},
  {"action": "DEFINE_FORWARD_TEST_GRADUATION", "reason": "8th cycle requesting. No criteria defined. Cannot promote/demote forward tests without this."}
]
```

---

## Executive Summary

**Zero new ACCEPTs. Pipeline self-regenerating. Claude specs blocked 4th cycle. 9 specs, 27+ variants sit idle.**

Since U26, no additional backtests have completed — the 36 zero-trade runs from earlier today remain the latest. But the pipeline has not stopped: 3 new strategy specs (489f8bcaea8f, 88cf9e406e3d, d7a7a5e46d09), 3 new theses, and 2 new promotion runs were generated AFTER the 102+ epidemic was documented. The pipeline is actively producing offspring that will generate more zero-trade backtests when they run. The waste backlog is growing, not shrinking.

The Claude spec portfolio is the largest and most complete it has ever been: **9 specs covering 6 distinct indicator mechanism families** (Vortex transition, KAMA adaptive, CCI confirmation, T3 smoothing, ALMA Gaussian, EMA200 structural gating) with 27+ variants. None have been backtested. The earliest (ALMA Vortex, T3 EMA200, CCI KAMA) are now blocked 4 consecutive cycles. At the validated 22% ACCEPT rate, approximately 2 new ACCEPTs are being prevented per cycle of delay.

**The pipeline is no longer just dead — it is self-reinforcing waste.** It fails, generates remediation specs from failures, those fail identically, generating more specs. Meanwhile it also generates entirely new specs via thesis-promotion that also fail. The generation rate exceeds the consumption rate, so the junk backlog grows. Halting backtesting alone is insufficient — spec generation itself must stop.

Brain: 26 objects. No confidence changes (no new trade data). 10 unique ACCEPTs unchanged.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| **Pipeline self-regeneration** | 3 new specs + 2 promotions generated AFTER 102+ epidemic | **NEW — KILL GENERATION** |
| **Directive remediation loop** | 102+ consecutive 0-trade runs, crosses day boundary | **CIRCULAR — KILL** |
| **Claude spec starvation** | 9 specs, 27+ variants blocked 4+ cycles (U24→U27) | **CRITICAL BLOCKER** |
| **Pipeline spec architecture** | EMA+RSI+ATR+confidence_threshold = 0 trades across 102+ runs | STRUCTURALLY DEAD |
| **Pipeline directive enforcement** | 0/28 machine directives read or applied | DEAD |
| **Recombine system** | Still generates BTC 1h specs despite EXCLUDE_ASSET:BTC | BROKEN |
| OBV volume confirmation | PF=1.094, noise not edge | DEAD |
| BTC all strategies | 0 ACCEPTs across 800+ outcomes | DEAD |
| 1h Vortex | v2c PF=0.816, v3b PF=0.803 | DEAD |

---

## Promising Directions

### Priority 0: Execute the 9 Claude specs (27+ variants)

The complete Claude spec portfolio, all ready to run on ETH 4h:

| Spec ID | Mechanism | Variants | Thesis |
|---------|-----------|----------|--------|
| claude-a7f3b1c2 | ALMA + Vortex | 4 | Gaussian smoothing reduces whipsaw vs EMA |
| claude-c9b0e2f7 | T3 + EMA200 Gate | 4 | Triple-smoothed EMA + macro filter |
| claude-e5d8f4a9 | CCI + KAMA | 4 | Mean-reversion with adaptive filtering |
| claude-d4e1f8a3 | Supertrend CCI 4h port | 3 | 1h near-miss PF=1.480, port to reduce DD |
| claude-b7c2a9e6 | EMA200 Vortex v3 tight | 4 | DD reduction from 30% to sub-20% |
| claude-f3a8d5b1 | MACD + Vortex | 3 | Dual-confirmed momentum shift |
| claude-stmacd01 | Supertrend + MACD | 3 | Supertrend direction + MACD confirmation |
| claude-kmrsi01a | KAMA + RSI | 3 | Isolate KAMA edge mechanism |
| claude-e2macd01 | EMA200 + MACD | 2 | Macro transition + momentum confirm |

**Expected yield: ~6 out of 30 variants should ACCEPT (22% historical rate). This is the ENTIRE research frontier.**

### Priority 1: Transition-detection expansion with new indicators
TREX histogram, TASC DM (Hilbert transform), TRIX_14 — all mathematically grounded transition detectors. Extends the thesis behind 6 of 10 ACCEPTs. Requires new dataframe columns.

### Priority 2: Forward-test lifecycle
Define graduation criteria. 2 strategies live, 2 candidates queued. No resolution mechanism.

---

## Template Health

| Template | ACCEPTs | Best PF | Status |
|----------|---------|---------|--------|
| spec_rules (Claude) | 10 | 2.034 | **ACTIVE — ALL ACCEPTs** |
| vortex_transition | 6 | 2.034 | CHAMPION (FWD-TEST) |
| supertrend_follow | 7 | 1.921 | STRONG (FWD-TEST) |
| ichimoku_tk_transition | 1 | 1.604 | ACCEPT |
| ema200_vortex | 1 | 1.969 | ACCEPT (conditional — DD=30%) |
| macd_confirmation | 9 | 1.712 | STRONG (SATURATED) |
| kama_stoch_pullback | 1 | 1.857 | ACCEPT (FWD-TEST CANDIDATE) |
| rsi_pullback | 5 | 1.442 | GOOD (SATURATED) |
| cci_chop_fade | 1 | 1.255 | STABLE |
| supertrend_cci | 0 | 1.480 (1h) | NEAR-MISS — spec claude-d4e1f8a3 ready |
| kama_vortex_divergence | 0 | — | UNTESTED |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## ACCEPT Leaderboard (Top 14 — unchanged from U25)

| Rank | Strategy | PF | DD | Trades | Key Regime | Status |
|------|----------|----|----|--------|------------|--------|
| 1 | Vortex Transition v3a (ETH 4h) | 2.034 | 15.2% | 84 | Trans 3.886, ALL | FWD-TEST LIVE |
| 2 | EMA200 Vortex v2 12:1 (ETH 4h) | 1.969 | 30.0% | 52 | Trans 4.321 RECORD | CONDITIONAL (DD) |
| 3 | Supertrend 8:1 tail (ETH 4h) | 1.921 | 10.9% | 85 | Rang 2.914, ALL | FWD-TEST LIVE |
| 4 | Supertrend ultra ADX10 8:1 | 1.907 | 12.9% | 99 | Rang 2.558 | ACCEPT |
| 5 | Vortex v2c (ETH 4h) | 1.892 | 12.3% | 84 | Trans 2.986, ALL | ACCEPT |
| 6 | Vortex v3b (ETH 4h) | 1.885 | 11.8% | 84 | Trans 2.250, ALL | ACCEPT |
| 7 | KAMA Stoch v1 8:1 (ETH 4h) | 1.857 | 10.1% | 42 | Rang 4.870, ALL | FWD-TEST CANDIDATE |
| 8 | Vortex v2a (ETH 4h) | 1.735 | 11.4% | 80 | ALL | ACCEPT |
| 9 | MACD 7:1 tail (ETH 4h) | 1.712 | 7.5% | 161 | Rang 2.060 | ACCEPT |
| 10 | Ichimoku TK v1 (ETH 4h) | 1.604 | 20.4% | 111 | ALL | FWD-TEST CANDIDATE |
| 11 | MACD 6:1 (ETH 4h) | 1.460 | 8.2% | 170 | ALL | ACCEPT |
| 12 | RSI pullback 8:1 (ETH 4h) | 1.442 | 7.1% | 156 | ALL | ACCEPT |
| 13 | Pipeline template_div | 1.419 | 10.5% | 140 | Trend 2.150 | ACCEPT |
| 14 | CCI Chop Fade v2 (ETH 4h) | 1.255 | 16.4% | 179 | ALL | ACCEPT |

---

## Regime Insights

- **No new regime data.** 102+ zero-trade backtests produce zero regime analysis. Knowledge frozen since U24.
- **Transitional remains highest-alpha regime.** EMA200 Vortex v2 trans PF=4.321 (record). 6/10 ACCEPTs use transition-detection.
- **Ranging is universal base.** Every ACCEPT profitable in ranging (PF 1.12-4.87).
- **Trending is the filter.** Only transition-detecting (Vortex) and adaptive (KAMA) strategies survive trending without regime gate.
- **No empirical challenge possible this cycle.** Existing beliefs cannot be tested while pipeline consumes all capacity.

---

## Recommended Directives

1. **HALT PIPELINE + SPEC GENERATION** — Not just backtesting — halt generation too. Pipeline is producing new specs (3 this cycle) that will produce more 0-trade waste. Stop the source.
2. **EXECUTE ALL 9 CLAUDE SPECS** — 27+ variants on ETH 4h. Expected ~6 ACCEPTs. 4th cycle of delay for earliest specs.
3. **ADD TRIX_14, TREX, TASC DM INDICATORS** — Transition-detection expansion blocked waiting for new dataframe columns. 3rd cycle requesting.
4. **DEFINE FORWARD-TEST GRADUATION** — 8th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15% = graduate. PF < 0.8 or DD > 25% = demote.
5. **PROMOTE KAMA Stoch v1 + Ichimoku TK v1** — Both decorrelated ACCEPTs ready for forward-test lanes 3 and 4.

---

## Doctrine Gaps

1. **No spec generation rate-limiting.** Pipeline generates specs independently of backtest capacity. Waste backlog grows unchecked. Need: generation pauses when backtest queue > N.
2. **No circuit-breaker doctrine.** 102+ zero-trade runs would be caught at 5-10 with a simple rule. Still no automatic halt.
3. **No spec priority routing.** Claude specs and pipeline specs compete equally for backtest capacity despite 22% vs ~0% ACCEPT rates.
4. **No forward-test lifecycle.** Start, monitor, graduate, demote — none defined. 8th cycle requesting.
5. **No indicator request pipeline.** TRIX requested U24. TREX and TASC DM requested U26. No process to add indicators.
6. **Stale doctrine references.** All outcome notes reference doctrine items from 2026-02-26 (8+ days). Doctrine not evolving.

---

## Suggestions For Asz

- **Kill the pipeline AND its spec generation.** Halting backtests isn't enough — the pipeline generated 3 new junk specs today even without executing them. Stop thesis→spec→promotion entirely.
- **Run all 9 Claude specs** immediately. 27+ variants ready. This is 4 cycles of delayed research. Expected ~6 new ACCEPTs.
- **Add TRIX_14, TREX histogram, TASC DM** to the dataframe. Transition-detection expansion is the most promising research direction and it's blocked on indicators.
- **Define forward-test graduation criteria.** 8th cycle requesting. Proposed: 30 days live, PF > 1.2, DD < 15%.
- **Consider adding a signal pre-check** to the backtester: verify that entry conditions co-fire on at least 0.5% of bars before committing a full backtest run. Would prevent all 102+ wasted runs.
