# Strategy Advisory — 2026-03-05 (Update 28)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 10 new backtests (all 0 trades, same spec), 100+ pipeline specs still generating, 9 Claude specs blocked 5th cycle, 0 NEW ACCEPTs
**Prior advisory:** 2026-03-05 (Update 27)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 28 cycles. Pipeline STILL generating BTC 1h specs despite this directive."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD accumulation prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles. Consuming backtest slots for zero output."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "CRITICAL U28: 9 Claude specs blocked 5 CONSECUTIVE CYCLES. 22% ACCEPT rate vs pipeline ~0%. ~10 ACCEPTs delayed cumulatively."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "ESCALATED U28: 112+ consecutive 0-trade backtests. Same spec re-tested 10x this cycle with 0 trades."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "ESCALATED U28: spec-20260305-5df8f61c0c71 backtested 10 times, 0 trades every time. No circuit breaker."},
  {"action": "HALT_PIPELINE", "reason": "ESCALATED U28: 100+ new strategy specs generated in 20260305/ directory. Pipeline running at full generation rate despite total failure."},
  {"action": "HALT_SPEC_GENERATION", "reason": "ESCALATED U28: Pipeline generating 100+ specs on day with 0% success rate. BTC 1h still being targeted. Generation must stop."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT. BLOCKED 6 cycles."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop. BLOCKED 5 cycles."},
  {"action": "TEST_TEMPLATE", "target": "kama_vortex_divergence", "priority": 2, "reason": "NEW U28: Built-in template in signal_templates.py, NEVER tested. Combines two proven ACCEPT families (KAMA + Vortex). Detects exhaustion via KAMA flattening + Vortex crossover."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "TRIX triple-smoothed EMA. Transition-detection candidate. Requested since U24 (5 cycles)."},
  {"action": "INDICATOR_REQUEST", "target": "TREX_histogram", "reason": "Research card — triple exponentially smoothed MA histogram. Transition-detection via zero-cross."},
  {"action": "INDICATOR_REQUEST", "target": "TASC_DM_hilbert", "reason": "Research card — Hilbert transform directional movement. Phase detection for regime transitions."},
  {"action": "DEFINE_FORWARD_TEST_GRADUATION", "reason": "9th cycle requesting. No criteria defined. Cannot promote/demote forward tests without this."}
]
```

---

## Executive Summary

**Zero new ACCEPTs. 5th consecutive cycle of Claude spec blockage. Pipeline generating 100+ new specs per day at 0% success rate. ~10 cumulative ACCEPTs delayed.**

Since U27, 10 additional backtests completed — all zero trades from a single spec (strategy-spec-20260305-5df8f61c0c71) tested across 3 directive variants, 2 assets, and 2 timeframes. Total zero-trade epidemic: **112+ consecutive backtests** across 3 days. Meanwhile, the strategy_specs/20260305/ directory contains **100+ newly generated pipeline specs**, many targeting BTC 1h in direct violation of EXCLUDE_ASSET:BTC.

The 9 Claude specs (27+ variants across 6 mechanism families) are now blocked **5 consecutive cycles** (U24→U28). At 22% ACCEPT rate, approximately **10 new ACCEPTs have been prevented** cumulatively. The entire research program has been frozen since U24 — no new trade data, no regime analysis, no belief evolution.

**New discovery this cycle:** The `kama_vortex_divergence` template has been sitting in signal_templates.py since it was built, **never tested**. It combines KAMA flattening (adaptive speed → exhaustion) with Vortex crossover (transition detection) — the two indicator families behind 7 of 10 ACCEPTs. This is a zero-effort test opportunity.

Brain: 26 objects → 28 (2 updated, 1 new fact). 10 unique ACCEPTs unchanged.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| **Pipeline 100+ specs/day at 0%** | 100+ specs in 20260305/, 0 trades ever | **ESCALATED — KILL GENERATION** |
| **Claude spec starvation** | 9 specs, 27+ variants blocked 5 cycles (U24→U28) | **CRITICAL — ~10 ACCEPTs delayed** |
| **Single-spec loop** | spec-5df8f61c0c71 tested 10x, 0 trades every time | **LOOP CONFIRMED** |
| **BTC 1h generation** | Recent specs target BTC 1h despite EXCLUDE_ASSET | **DIRECTIVE IGNORED** |
| **Directive enforcement** | 0/29 machine directives applied | DEAD |
| OBV volume confirmation | PF=1.094, noise not edge | DEAD |
| BTC all strategies | 0 ACCEPTs across 800+ outcomes | DEAD |
| 1h Vortex | v2c PF=0.816, v3b PF=0.803 | DEAD |

---

## Promising Directions

### Priority 0: Execute the 9 Claude specs (27+ variants)

Unchanged from U27. The complete Claude spec portfolio, all ready to run on ETH 4h:

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

### Priority 1: Test kama_vortex_divergence template (NEW)

The `kama_vortex_divergence` template exists in `signal_templates.py` but has **never been backtested**. It detects exhaustion via KAMA flattening + Vortex crossover + ATR gate. This combines the two proven all-regime families (KAMA adaptive + Vortex transition) in an exhaustion-detection architecture — a mechanism not yet tested. Zero spec-writing effort required.

### Priority 2: Transition-detection expansion with new indicators

TREX histogram, TASC DM (Hilbert transform), TRIX_14 — all mathematically grounded transition detectors. Extends the thesis behind 6 of 10 ACCEPTs. Requires new dataframe columns. 5th cycle requesting TRIX.

### Priority 3: Forward-test lifecycle

Define graduation criteria. 2 strategies live, 2 candidates queued. No resolution mechanism. 9th cycle requesting.

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
| supertrend_cci | 0 | 1.480 (1h) | NEAR-MISS — 4h port blocked 6 cycles |
| **kama_vortex_divergence** | 0 | — | **UNTESTED — NEW PRIORITY** |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## ACCEPT Leaderboard (Top 14 — unchanged from U24)

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

- **No new regime data.** 112+ zero-trade backtests produce zero regime analysis. Knowledge frozen since U24 (5 cycles).
- **Transitional remains highest-alpha regime.** EMA200 Vortex v2 trans PF=4.321 (record). 6/10 ACCEPTs use transition-detection.
- **Ranging is universal base.** Every ACCEPT profitable in ranging (PF 1.12-4.87).
- **Trending is the filter.** Only transition-detecting (Vortex) and adaptive (KAMA) strategies survive trending without regime gate.
- **Exhaustion-detection untested.** kama_vortex_divergence template targets exhaustion (trend ending) — a mechanism distinct from transition-detection (trend starting). Could reveal new regime dynamics.
- **No empirical challenge possible.** Existing beliefs cannot be tested or updated while pipeline consumes all capacity.

---

## Recommended Directives

1. **HALT PIPELINE + SPEC GENERATION** — Pipeline generated 100+ specs today at 0% success rate, many targeting BTC 1h. Stop generation entirely.
2. **EXECUTE ALL 9 CLAUDE SPECS** — 27+ variants on ETH 4h. Expected ~6 ACCEPTs. 5th cycle of delay. ~10 cumulative ACCEPTs prevented.
3. **TEST kama_vortex_divergence TEMPLATE** — Built-in, never tested, combines two proven ACCEPT families. Zero spec effort.
4. **ADD TRIX_14, TREX, TASC DM INDICATORS** — 5th cycle requesting TRIX. Transition-detection expansion blocked on indicators.
5. **DEFINE FORWARD-TEST GRADUATION** — 9th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15% = graduate. PF < 0.8 or DD > 25% = demote.
6. **PROMOTE KAMA Stoch v1 + Ichimoku TK v1** — Both decorrelated ACCEPTs ready for forward-test lanes 3 and 4.

---

## Doctrine Gaps

1. **No spec generation rate-limiting.** Pipeline generates 100+ specs/day independently of backtest capacity. Waste grows unchecked.
2. **No circuit-breaker doctrine.** 112+ zero-trade runs. Same spec tested 10x. Still no automatic halt.
3. **No spec priority routing.** Claude specs and pipeline specs compete equally despite 22% vs ~0% ACCEPT rates.
4. **No forward-test lifecycle.** 9th cycle requesting. Start, monitor, graduate, demote — none defined.
5. **No indicator request pipeline.** TRIX requested U24 (5 cycles ago). No process to add indicators.
6. **Stale doctrine references.** All outcome notes reference doctrine items from 2026-02-26 (9+ days). Doctrine not evolving.
7. **No template coverage tracking.** kama_vortex_divergence sat untested for weeks until manual discovery. No system to flag untested templates.

---

## Suggestions For Asz

- **Kill the pipeline AND its spec generation.** 100+ new specs generated today, all will produce 0 trades. The waste machine is accelerating, not slowing down.
- **Run all 9 Claude specs immediately.** 5 cycles of delayed research. ~10 cumulative ACCEPTs prevented. This is the single highest-ROI action available.
- **Run kama_vortex_divergence template on ETH 4h.** Built-in, never tested, zero spec effort. Combines two proven families.
- **Add TRIX_14 to the dataframe.** 5th cycle requesting. Single indicator addition, extends highest-alpha research direction.
- **Define forward-test graduation criteria.** 9th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15%.
- **Add template coverage alerting.** Flag any template in signal_templates.py with 0 backtests. Would have caught kama_vortex_divergence weeks ago.
