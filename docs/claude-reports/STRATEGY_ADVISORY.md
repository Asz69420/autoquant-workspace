# Strategy Advisory — 2026-03-05 (Update 26)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 36 new backtests (all 0-trade), 26 brain objects (4 updated), 0 NEW ACCEPTs
**Prior advisory:** 2026-03-04 (Update 25)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 26 cycles. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD accumulation prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles. Consuming backtest slots for zero output."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "CRITICAL U26: 3 Claude specs blocked 3 cycles. 22.2% ACCEPT rate vs pipeline ~0%. 9 variants ready to run."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "ESCALATED U26: 102+ consecutive 0-trade backtests. Loop crosses day boundary (03-04 → 03-05). Consuming ALL backtest capacity."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "ESCALATED U26: Pipeline at 102+ zero-trade. 36 new today. Should have halted 97+ backtests ago."},
  {"action": "HALT_PIPELINE", "reason": "NEW U26: 102+ zero-trade is conclusive. Not circuit-break — full halt. Reallocate ALL capacity to Claude specs."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT. BLOCKED 4 cycles."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop. BLOCKED 3 cycles."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "TRIX triple-smoothed EMA. Transition-detection candidate via zero-cross. Requested since U24."},
  {"action": "INDICATOR_REQUEST", "target": "TREX_histogram", "reason": "NEW U26: Research card — triple exponentially smoothed MA histogram. Transition-detection via zero-cross."},
  {"action": "INDICATOR_REQUEST", "target": "TASC_DM_hilbert", "reason": "NEW U26: Research card — Hilbert transform directional movement. Mathematical phase detection for regime transitions."},
  {"action": "DEFINE_FORWARD_TEST_GRADUATION", "reason": "7th cycle requesting. No criteria defined. Cannot promote/demote forward tests without this."}
]
```

---

## Executive Summary

**Zero new ACCEPTs. Zero-trade epidemic reaches 102+. Three Claude specs blocked for 3 consecutive cycles.** The pipeline continues burning 100% of backtest capacity on directive-loop variants that produce zero trades. 36 new backtests today (2026-03-05) — all 0 trades, all directive-generated, all sharing the same EMA+RSI+ATR+confidence_threshold architecture. The loop has crossed a day boundary with no circuit-breaker intervention.

Three well-designed Claude specs (ALMA Vortex, T3 EMA200 Gate, CCI KAMA Reversal — 9 variants total) sit ready to run. All follow brain rules: 2 entry conditions, 8:1 R:R, ETH 4h. At 22% historical ACCEPT rate, ~2 should produce tradeable results. They remain unexecuted because the pipeline consumes every backtest slot.

Research cards this cycle identify two new transition-detection candidates: **TREX** (triple exponentially smoothed MA histogram, SoheilPKO) and **TASC Directional Movement** (Hilbert transform, SoheilPKO). Both detect regime shift moments using mathematical smoothing — aligning directly with our validated transition-detection thesis. Neither indicator exists in the dataframe yet.

Brain: 4 objects updated with extended evidence. 26 objects total. 10 unique ACCEPTs unchanged.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| **Directive remediation loop** | 102+ consecutive 0-trade runs (was 66+ at U25), crosses day boundary | **CIRCULAR — KILL** |
| **Pipeline spec architecture** | EMA+RSI+ATR+confidence_threshold = 0 trades across 102+ runs | STRUCTURALLY DEAD |
| **Claude spec starvation** | 3 specs, 9 variants blocked 3 cycles (U24→U26) | **CRITICAL BLOCKER** |
| **Pipeline directive enforcement** | 0/27 machine directives read or applied | DEAD |
| **Recombine system** | Still generates BTC 1h specs despite EXCLUDE_ASSET:BTC | BROKEN |
| OBV volume confirmation | PF=1.094, noise not edge | DEAD |
| BTC all strategies | 0 ACCEPTs across 800+ outcomes | DEAD |
| 1h Vortex | v2c PF=0.816, v3b PF=0.803 | DEAD |

---

## Promising Directions

### Priority 0: Execute the 3 blocked Claude specs
ALMA Vortex (a7f3b1c2), T3 EMA200 Gate (c9b0e2f7), CCI KAMA Reversal (e5d8f4a9) — 9 variants ready. All follow brain rules (2 entry conditions, 8:1 R:R, ETH 4h). At 22% ACCEPT rate, ~2 should hit. **This is the ONLY path to progress. BLOCKED 3 cycles by pipeline.**

### Priority 1: Supertrend CCI v4 on ETH 4h
1h near-miss PF=1.480. Every 1h→4h port improved PF by 0.5-1.3 points. Highest-probability next ACCEPT after the blocked specs. **Needs spec written. BLOCKED 4 cycles.**

### Priority 2: EMA200 Vortex v3 with tighter stops
v2 PF=1.969, trans PF=4.321 (record). DD=30% must drop below 20%. Reduce stop_atr_mult from 1.5 to 1.0. **BLOCKED 3 cycles.**

### Priority 3: Transition-detection expansion with new indicators
TREX histogram zero-cross and TASC DM (Hilbert transform) are mathematically grounded transition detectors from research cards. Request indicators, then design specs. Extends the thesis behind 6 of our 10 ACCEPTs.

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
| supertrend_cci | 0 | 1.480 (1h) | NEAR-MISS |
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

- **Transitional remains highest-alpha regime.** EMA200 Vortex v2 trans PF=4.321 (record). Vortex v3a trans PF=3.886. Ichimoku TK v1 trans PF=2.44. Transition-detection strategies dominate.
- **Ranging is universal base.** Every ACCEPT profitable in ranging (PF 1.12-4.87). KAMA Stoch v1 ranging PF=4.87 is the single-regime record.
- **Trending is the filter.** Non-adaptive strategies lose in trending. Only Vortex (transition) and KAMA (adaptive) survive trending regime.
- **No new regime data this cycle.** 102+ zero-trade backtests = no trades = no regime analysis possible. Stagnation is complete.

---

## Recommended Directives

1. **HALT PIPELINE** — 102+ zero-trade backtests is conclusive. Every additional run is confirmed waste. Full halt, not circuit-break.
2. **EXECUTE CLAUDE SPECS** — ALMA Vortex (a7f3b1c2), T3 EMA200 (c9b0e2f7), CCI KAMA (e5d8f4a9). 9 variants, ETH 4h. The only path to new ACCEPTs.
3. **ADD TREX + TASC DM INDICATORS** — Research-backed transition-detection candidates. TREX = triple exponentially smoothed MA histogram. TASC DM = Hilbert transform phase detection.
4. **DEFINE FORWARD-TEST GRADUATION** — 7th cycle requesting. Proposed: 30 days live, PF > 1.2, DD < 15% = graduate. PF < 0.8 or DD > 25% = demote.
5. **PROMOTE KAMA Stoch v1 + Ichimoku TK v1** — Both decorrelated ACCEPTs ready for forward-test.

---

## Doctrine Gaps

1. **No circuit-breaker doctrine.** No principle for halting automation after consecutive failures. 102+ zero-trade epidemic would be caught at 5-10 with a simple rule.
2. **No spec priority routing.** No doctrine for priority ordering when Claude specs and pipeline specs compete for capacity.
3. **No forward-test lifecycle.** Start, monitor, graduate, demote — none defined. Forward tests accumulate with no resolution.
4. **No indicator request pipeline.** TRIX requested U24. TREX and TASC DM requested U26. No process to add indicators.
5. **Stale doctrine references.** All outcome notes reference doctrine items from 2026-02-26 (8+ days). Doctrine not evolving.

---

## Suggestions For Asz

- **Kill the pipeline.** Not pause — kill. 102+ zero-trade across 2 days is conclusive. Reallocate ALL backtest capacity to Claude specs.
- **Run the 3 Claude specs** (ALMA Vortex, T3 EMA200, CCI KAMA) immediately. They are the entire research frontier, blocked 3 cycles.
- **Add TRIX_14, TREX, and TASC DM to the dataframe.** Next transition-detection candidates. Without them the most promising research direction is stuck.
- **Define forward-test graduation criteria.** 7 cycles overdue. Proposed: 30 days + PF > 1.2 + DD < 15% = graduate to small live allocation.
- **Write Supertrend CCI v4 spec for ETH 4h** — highest-probability next ACCEPT from 1h near-miss PF=1.480.
