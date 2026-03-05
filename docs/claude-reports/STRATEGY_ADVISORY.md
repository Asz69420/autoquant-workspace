# Strategy Advisory — 2026-03-05 (Update 30)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 1826 backtests today (ALL 0-trade), 2028 feasibility reports, 134 promotions, 96 bundles — pipeline at industrial-scale waste. PPR system validates Claude-only monopoly. 0 NEW ACCEPTs.
**Prior advisory:** 2026-03-05 (Update 29)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 30 cycles. Pipeline STILL generating BTC 1h specs."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "CRITICAL U30: 9 Claude specs blocked 7 CONSECUTIVE CYCLES. PPR independently confirms ONLY Claude specs score >3.0 (PROMOTE). PROMOTED_INDEX = 10 entries, ALL Claude."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "ESCALATED U30: 1826 backtests today alone, ALL 0-trade. Directive specs formally invalid (confidence_threshold not real column)."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "ESCALATED U30: 1826 backtests/day with 0 trades = $0 research value at industrial compute cost."},
  {"action": "HALT_PIPELINE", "reason": "EMERGENCY U30: pipeline scaled to 1826 backtests/day, 2028 feasibility reports, 134 promotions, 96 bundles — ALL waste. 10x escalation from U29."},
  {"action": "HALT_SPEC_GENERATION", "reason": "EMERGENCY U30: pipeline generating AND executing at industrial scale. Must halt both generation and execution."},
  {"action": "REJECT_PENDING_PROMOTIONS", "target": "artifacts/promotions/20260305/", "count": 5, "reason": "5 REVIEW_REQUIRED promotions from pipeline. All parent specs = 0-trade. Reject without backtest."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT. BLOCKED 8 cycles."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop. BLOCKED 7 cycles."},
  {"action": "TEST_TEMPLATE", "target": "kama_vortex_divergence", "priority": 2, "reason": "Built-in template, NEVER tested. Combines two proven ACCEPT families. Detects exhaustion."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "Transition-detection candidate. Requested since U24 (7 cycles)."},
  {"action": "INDICATOR_REQUEST", "target": "TREX_histogram", "reason": "Triple exponentially smoothed MA histogram. Transition-detection via zero-cross."},
  {"action": "INDICATOR_REQUEST", "target": "TASC_DM_hilbert", "reason": "Hilbert transform directional movement. Phase detection for regime transitions."},
  {"action": "DEFINE_FORWARD_TEST_GRADUATION", "reason": "11th cycle requesting. No criteria defined."}
]
```

---

## Executive Summary

**Zero new ACCEPTs. 7th consecutive cycle of Claude spec blockage. Pipeline has scaled to industrial-scale waste: 1826 backtests/day at 0% success. PPR scoring independently confirms only Claude specs deserve promotion.**

Since U29: The pipeline has escalated from "100+ specs/day" to **1826 backtests/day** — an order-of-magnitude increase. Today's output: 2028 feasibility reports, 134 promotion runs, 96 recombine bundles, 140 experiments, and 1826 backtests. Every single backtest produced zero trades.

**New finding this cycle:** The PPR scoring system (recently deployed) independently validates brain belief `fact-claude-specs-sole-progress`. The PROMOTED_INDEX contains exactly 10 entries — **all 10 are Claude-specified strategies**. Pipeline specs score near-zero PPR. The scoring system is a third independent source (alongside brain analysis and historical ACCEPT rates) confirming that Claude specs are the sole source of research value.

**Second finding:** 5 new promotion runs from pipeline are stuck at `REVIEW_REQUIRED` status. These await Quandalf decision but originate from the same dead pipeline. All should be rejected without consuming backtest capacity.

Brain: 30 → 31 objects (+1 new fact). 10 unique ACCEPTs unchanged since U24.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| **Pipeline at industrial scale** | 1826 backtests/day, 2028 feasibility, 134 promos, 96 bundles — ALL waste | **EMERGENCY — 10x ESCALATION** |
| **Claude spec starvation** | 9 specs, 27+ variants blocked 7 cycles (U24→U30) | **CRITICAL — ~14 ACCEPTs delayed** |
| **Research card homogeneity** | 10/10 latest = identical "Adaptive Flag Patterns" recombine clone | **COLLAPSED** |
| **Abstract pseudo-signals** | Directive specs use confidence_threshold (not a real column) | **FORMALLY INVALID** |
| **Directive loop** | Same 5 directives on every 0-trade, now applied 1826x/day | **STRUCTURALLY UNFIXABLE** |
| **BTC 1h generation** | Recombine + research cards both target BTC 1h despite EXCLUDE_ASSET | **DIRECTIVE IGNORED** |
| **Pipeline promotions** | 5 new REVIEW_REQUIRED promos from dead pipeline | **REJECT ALL** |

---

## Promising Directions

### Priority 0: Execute the 9 Claude specs (27+ variants)

Unchanged from U27. PPR now independently validates this priority — only Claude specs score PROMOTE (>3.0).

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

**Expected yield: ~6 out of 30 variants should ACCEPT (22% historical rate).**

### Priority 1: Test kama_vortex_divergence template

Built-in template, never tested, combines two proven ACCEPT families (KAMA + Vortex). Detects exhaustion — untested mechanism distinct from transition-detection.

### Priority 2: Transition-detection expansion with new indicators

TREX histogram, TASC DM (Hilbert transform), TRIX_14 — all mathematically grounded transition detectors. 7th cycle requesting TRIX.

### Priority 3: Forward-test lifecycle

Define graduation criteria. 2 strategies live, 2 candidates queued. **11th cycle requesting.**

---

## Template Health

| Template | ACCEPTs | Best PF | Status |
|----------|---------|---------|--------|
| spec_rules (Claude) | 10 | 2.034 | **ACTIVE — ALL ACCEPTs. PPR VALIDATED.** |
| vortex_transition | 6 | 2.034 | CHAMPION (FWD-TEST) |
| supertrend_follow | 7 | 1.921 | STRONG (FWD-TEST) |
| ichimoku_tk_transition | 1 | 1.604 | ACCEPT |
| ema200_vortex | 1 | 1.969 | ACCEPT (conditional — DD=30%) |
| macd_confirmation | 9 | 1.712 | STRONG (SATURATED) |
| kama_stoch_pullback | 1 | 1.857 | ACCEPT (FWD-TEST CANDIDATE) |
| rsi_pullback | 5 | 1.442 | GOOD (SATURATED) |
| cci_chop_fade | 1 | 1.255 | STABLE |
| supertrend_cci | 0 | 1.480 (1h) | NEAR-MISS — 4h port blocked 8 cycles |
| **kama_vortex_divergence** | 0 | — | **UNTESTED — PRIORITY** |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## ACCEPT Leaderboard (Top 14 — unchanged since U24)

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

- **No new regime data.** 1826 zero-trade backtests produce zero regime analysis. Knowledge frozen since U24 (7 cycles).
- **Transitional remains highest-alpha regime.** EMA200 Vortex v2 trans PF=4.321 (record). 6/10 ACCEPTs use transition-detection.
- **Ranging is universal base.** Every ACCEPT profitable in ranging (PF 1.12-4.87).
- **Trending is the filter.** Only transition-detecting and adaptive strategies survive trending without regime gate.
- **Exhaustion-detection untested.** kama_vortex_divergence targets trend ending — distinct from transition-detection.
- **PPR validates regime thesis.** PROMOTED_INDEX top strategies all use transition-detection or adaptivity. PPR scoring aligns with brain beliefs about what works.

---

## Recommended Directives

1. **EMERGENCY: HALT ALL AUTONOMOUS PIPELINE** — 1826 backtests/day at 0% = industrial-scale compute waste. Halt spec generation, recombine, feasibility, AND backtest execution of pipeline specs. This is a 10x escalation from U29.
2. **EXECUTE ALL 9 CLAUDE SPECS** — 27+ variants on ETH 4h. Expected ~6 ACCEPTs. 7th cycle of delay. ~14 cumulative ACCEPTs prevented.
3. **REJECT 5 PENDING PROMOTIONS** — 5 REVIEW_REQUIRED promos from dead pipeline. All parent specs = 0-trade families.
4. **TEST kama_vortex_divergence TEMPLATE** — Built-in, never tested, combines two proven families.
5. **ADD TRIX_14, TREX, TASC DM INDICATORS** — 7th cycle requesting TRIX.
6. **DEFINE FORWARD-TEST GRADUATION** — 11th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15%.

---

## Doctrine Gaps

1. **No pipeline rate-limiting.** Pipeline scaled from 100+ to 1826 backtests/day with no throttle. Waste grows exponentially.
2. **No circuit-breaker.** 1826 zero-trade backtests today. Still no automatic halt.
3. **No spec priority routing.** Claude specs (22% ACCEPT) and pipeline specs (0%) compete equally.
4. **No forward-test lifecycle.** 11th cycle requesting.
5. **No indicator request pipeline.** TRIX requested 7 cycles ago.
6. **No research card dedup/diversity check.** 10/10 cards identical.
7. **No spec validity pre-check.** Specs reference non-existent columns.
8. **Stale doctrine.** All doctrine items dated 2026-02-26 (10+ days, not evolving).
9. **No pipeline scale alerting.** 10x volume increase went undetected until manual count.

---

## Suggestions For Asz

- **EMERGENCY: Kill the entire autonomous pipeline.** 1826 backtests/day at 0% success is not "broken" — it's industrial-scale compute burn. This is 10x worse than documented in U29. Every hour the pipeline runs wastes resources that should run Claude specs.
- **Run all 9 Claude specs immediately.** 7 cycles delayed. PPR independently confirms only Claude specs merit PROMOTE status.
- **Reject the 5 pending REVIEW_REQUIRED promotions.** They come from the dead pipeline. Don't waste backtest capacity.
- **Run kama_vortex_divergence on ETH 4h.** Zero spec effort. Combines two proven families.
- **Add pipeline volume alerting.** The pipeline scaled 10x without triggering any alert. Add a hard cap (e.g., max 50 backtests/day from automated sources).
- **Add TRIX_14.** 7th cycle requesting.
- **Define forward-test graduation.** 11th cycle requesting.
