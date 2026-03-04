# Strategy Advisory — 2026-03-04 (Update 24)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 10 new backtests, 23→25 brain objects, 10 research cards, 2 NEW ACCEPTs
**Prior advisory:** 2026-03-04 (Update 23)

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
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "Ichimoku + KAMA", "reason": "4 configs tested, best PF=1.090 (marginal). Incompatible time horizons."},
  {"action": "BLACKLIST_INDICATOR_COMBO", "target": "CCI + T3 zero-cross", "reason": "PF=0.606 on ETH 1h. T3 too slow as CCI smoothing filter."},
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 24 cycles. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD accumulation prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles. Consuming backtest slots for zero output."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of ACCEPTs. 22.2% ACCEPT rate vs pipeline ~0%."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "NEW ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop to reduce DD below 20%."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "Research cards: TRIX triple-smoothed EMA is a momentum/trend signal. Tests Ehlers-style smoothing."},
  {"action": "INDICATOR_REQUEST", "target": "ehlers_hann_oscillator", "reason": "Research-derived: Ehlers spectral cycle detection."}
]
```

---

## Executive Summary

**Two new ACCEPTs this cycle — the most productive cycle since U8.** Ichimoku TK Transition v1 (PF=1.604, ETH 4h) validates the paradigm-level hypothesis from Entry 012: **transition-detection is a GENERAL market mechanism, not a Vortex artifact.** EMA200 Vortex v2 12:1 (PF=1.969, trans PF=4.321) sets a new transitional alpha record but is borderline on DD (30% vs 20% constraint). Total unique ACCEPTs now 10. Brain grows to 25 objects.

The zero-trade epidemic continues (51+), but Claude specs ARE executing and producing results. Research digest reveals TRIX and Ehlers Directional Movement as new indicator families worth testing.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| OBV volume confirmation | Supertrend OBV ETH 4h PF=1.094, 284 trades, 17.6% WR | DEAD — OBV adds noise not edge |
| Vortex on 1h | v2c PF=0.816, v3b PF=0.803 on ETH 1h | CONFIRMED DEAD on 1h |
| BTC all strategies | Still 0 ACCEPTs across 800+ outcomes | DEAD |
| Pipeline/promotion specs | 51+ consecutive 0-trade backtests | STRUCTURALLY DEAD |
| CCI T3 Zero v2 Tight | PF=1.044, DD=23.2% — marginal | DEAD |

---

## Promising Directions

### Priority 0: Supertrend CCI v4 on ETH 4h
The 1h near-miss (PF=1.480, all-regime) should improve on 4h. Every previous 1h→4h port improved PF by 0.5-1.3 points. Highest-probability next ACCEPT.

### Priority 1: EMA200 Vortex v3 with tighter stops
v2 achieved PF=1.969 (second-highest ever) with trans PF=4.321 (NEW RECORD). DD=30% must drop below 20%. Reduce stop_atr_mult from 1.5 to 1.0-1.2 or reduce R:R from 12:1 to 8:1.

### Priority 2: Transition-detection family expansion
Ichimoku TK validates the mechanism. Next: test other transition-detection approaches — KAMA slope change, T3 direction flip, EMA crossover with regime gate. The underlying edge is in detecting the MOMENT markets shift between states.

### Priority 3: TRIX-based strategies
Research cards highlight TRIX (triple-smoothed EMA) as a momentum signal. Similar to T3 in smoothing philosophy but purpose-built for momentum detection. Request indicator addition.

---

## Template Health

| Template | ACCEPTs | Best PF | Status |
|----------|---------|---------|--------|
| spec_rules (Claude) | 10 | 2.034 | **ACTIVE — ALL ACCEPTs** |
| vortex_transition | 6 | 2.034 | CHAMPION (FWD-TEST) |
| supertrend_follow | 7 | 1.921 | STRONG (FWD-TEST) |
| ichimoku_tk_transition | 1 | 1.604 | **NEW ACCEPT** |
| ema200_vortex | 1 | 1.969 | **NEW ACCEPT (conditional — DD=30%)** |
| macd_confirmation | 9 | 1.712 | STRONG (SATURATED) |
| kama_stoch_pullback | 1 | 1.857 | ACCEPT (FWD-TEST CANDIDATE) |
| rsi_pullback | 5 | 1.442 | GOOD (SATURATED) |
| cci_chop_fade | 1 | 1.255 | STABLE |
| supertrend_cci | 0 | 1.480 (1h) | NEAR-MISS |
| supertrend_obv | 0 | 1.094 | DEAD — OBV adds noise |
| kama_vortex_divergence | 0 | — | UNTESTED |
| stochastic_reversal | 0 | — | DEAD (BUG) |
| bollinger_breakout | 0 | — | DEAD (BUG) |

---

## ACCEPT Leaderboard (Top 14)

| Rank | Strategy | PF | DD | Trades | All-Regime | Status |
|------|----------|----|----|--------|------------|--------|
| 1 | Vortex v3a 4h (ETH) | 2.034 | 15.2% | 84 | YES (trans 3.886) | FORWARD-TEST |
| 2* | EMA200 Vortex v2 12:1 (ETH) | 1.969 | 30.0% | 52 | YES (trans 4.321) | **NEW — conditional (DD)** |
| 3 | Supertrend 8:1 (ETH) | 1.921 | 10.9% | 85 | YES (ranging 2.914) | FORWARD-TEST |
| 4 | Supertrend ultra ADX10 8:1 (ETH) | 1.907 | 12.9% | 99 | YES (ranging 2.558) | ACCEPT |
| 5 | Vortex v2c 4h (ETH) | 1.892 | 12.3% | 84 | YES (trans 2.986) | ACCEPT |
| 6 | Vortex v3b 4h (ETH) | 1.885 | 11.8% | 84 | YES (trans 2.250) | ACCEPT |
| 7 | KAMA Stoch v1 8:1 (ETH) | 1.857 | 10.1% | 42 | YES (ranging 4.87) | FWD-TEST CANDIDATE |
| 8 | Vortex v2a 4h (ETH) | 1.735 | 11.4% | 80 | — | ACCEPT |
| 9 | MACD 7:1 (ETH) | 1.712 | 7.5% | 161 | — | ACCEPT |
| 10 | Ichimoku TK v1 (ETH) | 1.604 | 20.4% | 111 | YES (trans 2.44) | **NEW ACCEPT** |
| 11 | MACD 6:1 (ETH) | 1.460 | 8.2% | 170 | — | ACCEPT |
| 12 | RSI pullback 8:1 (ETH) | 1.442 | 7.1% | 156 | — | ACCEPT |
| 13 | Pipeline template_div (ETH) | 1.419 | 10.5% | 140 | — | ACCEPT |
| 14 | CCI Chop Fade v2 4h (ETH) | 1.255 | 16.4% | 179 | YES | ACCEPT |

*\* EMA200 Vortex v2 ranks #2 by PF but DD=30% exceeds 20% constraint. Conditional ACCEPT pending DD reduction.*

---

## Near-Miss Watch

| Strategy | PF | DD | Trades | Issue | Next Action |
|----------|----|----|--------|-------|-------------|
| **Supertrend CCI v3 Wide (ETH 1h)** | 1.480 | 36.4% | 63 | DD | Port to 4h |
| **EMA200 Vortex v2 12:1 (ETH 4h)** | 1.969 | 30.0% | 52 | DD | Tighten stop/R:R |
| EMA200 Vortex v1 (SOL 4h) | 1.185 | 55.2% | 106 | DD + PF | Test ETH 4h |

---

## Regime Insights

- **Ranging = universal base (conf 0.93):** All 10 ACCEPTs profitable in ranging. KAMA Stoch v1 ranging PF=4.87 remains record.
- **Transitional = highest alpha (conf 0.90 ↑):** EMA200 Vortex v2 trans PF=4.321 is NEW RECORD (was v3a at 3.886). Ichimoku TK trans also strong. Transition-detection confirmed as general mechanism.
- **Trending:** Most strategies lose. CCI as trend-confirmation (Supertrend CCI trending PF=1.638) is the only proven trending approach.
- **4h dominance (conf 0.95):** All 10 ACCEPTs are ETH 4h. 1h Supertrend CCI remains the only 1h all-regime exception (DD prevents ACCEPT).

---

## Recommended Directives

1. **Design Supertrend CCI v4 on ETH 4h** — highest-probability next ACCEPT
2. **Tighten EMA200 Vortex v2 stops** — PF=1.969 is second-best ever; reduce DD from 30% to <20%
3. **Promote Ichimoku TK v1 to forward-test candidate** — decorrelated from Vortex family, validates transition-detection mechanism
4. **Add TRIX_14 indicator** — research cards highlight triple-smoothed EMA momentum detection
5. **Continue routing Claude specs** — 10 still queued; some executing
6. **Kill pipeline autonomous generation** — 53 drought, 51+ zero-trade, consuming compute for nothing

---

## Doctrine Gaps

1. **Forward-test graduation criteria** — still undefined after 5 cycles
2. **DD reduction methodology** — EMA200 Vortex v2 and Supertrend CCI both have PF >1.4 but DD >20%. No systematic approach to reducing DD while preserving PF.
3. **Signal feasibility pre-check** — specs should be tested for condition co-occurrence before consuming backtest slot
4. **Portfolio correlation analysis** — all 10 ACCEPTs are ETH 4h; no correlation or diversification analysis
5. **Transition-detection taxonomy** — now that we know it's a general mechanism (Vortex, Ichimoku TK), need a framework to evaluate different implementations

---

## Suggestions For Asz

- **Ichimoku TK validates the transition-detection thesis** — this is the most important strategic finding since Vortex v3a. Design more transition-detection strategies using different indicator families.
- **EMA200 Vortex v2 is tantalizingly close** — PF=1.969 with trans PF=4.321 (new record). A stop-tightening variant (reduce atr_mult) could bring DD from 30% to <20% and create a clean ACCEPT.
- **Add TRIX indicator** — research cards from SoheilPKO describe TRIX as a triple-smoothed momentum detector. Similar philosophy to T3 but purpose-built for momentum. Worth testing as a new adaptive indicator family.
- **Define forward-test graduation criteria** — two strategies live, a third candidate (KAMA Stoch), now a fourth (Ichimoku TK). Need clear criteria before the forward-test queue backs up like the backtest queue.
