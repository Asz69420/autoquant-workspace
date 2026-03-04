# Strategy Advisory — 2026-03-04 (Update 25)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 15+ new backtests (all 0-trade), 25→26 brain objects, 0 NEW ACCEPTs
**Prior advisory:** 2026-03-04 (Update 24)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 25 cycles. Even champion v3a loses (PF=0.743)."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 10 ACCEPTs are 4h. 1h shows promise but DD accumulation prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles. Consuming backtest slots for zero output."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "Claude specs = 100% of ACCEPTs. 22.2% ACCEPT rate vs pipeline ~0%. Pipeline consuming all backtest capacity."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "NEW U25: Directive system generates identical 5 remediation actions for every 0-trade failure. Variants fail identically. Circular loop. 66+ wasted backtests."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "NEW U25: Pipeline should auto-halt after 5 consecutive 0-trade runs from same spec family. Currently at 66+."},
  {"action": "MONITOR_FORWARD_TEST", "target": "vortex_transition_v3a", "status": "LIVE"},
  {"action": "MONITOR_FORWARD_TEST", "target": "supertrend_tail_harvester_8to1", "status": "LIVE"},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "kama_stoch_pullback_v1", "reason": "Third lane, decorrelated."},
  {"action": "FORWARD_TEST_CANDIDATE", "target": "ichimoku_tk_transition_v1", "reason": "ACCEPT PF=1.604. Decorrelated from Vortex family."},
  {"action": "DESIGN_SPEC", "target": "supertrend_cci_v4_4h", "priority": 0, "reason": "1h near-miss PF=1.480. 4h port = highest-probability next ACCEPT. BLOCKED by pipeline."},
  {"action": "DESIGN_SPEC", "target": "ema200_vortex_v3_tight_dd", "priority": 1, "reason": "v2 PF=1.969 but DD=30%. Tighten stop to reduce DD below 20%. BLOCKED."},
  {"action": "INDICATOR_REQUEST", "target": "TRIX_14", "reason": "Research cards: TRIX triple-smoothed EMA is a momentum/trend signal."},
  {"action": "INDICATOR_REQUEST", "target": "ehlers_hann_oscillator", "reason": "Research-derived: Ehlers spectral cycle detection."}
]
```

---

## Executive Summary

**Zero new ACCEPTs. The directive loop is the #1 blocker.** All 15+ backtests since U24 are pipeline-generated specs using the same EMA+RSI+ATR+confidence_threshold architecture — every one produced 0 trades. Zero-trade epidemic escalates to 66+. The directive system is now confirmed as a **circular loop**: every 0-trade outcome generates the same 5 remediation directives (GATE_ADJUST, ENTRY_RELAX, THRESHOLD_SWEEP, ENTRY_TIGHTEN, EXIT_CHANGE), which create variant specs that fail identically. No Claude specs have executed since U24. The recombine system is also generating specs on blacklisted asset/timeframe combos (BTC 1h) using the same broken template.

All U24 research priorities (Supertrend CCI v4 4h, EMA200 Vortex v3 tight stops, transition-detection expansion) remain unexecuted. Brain grows to 26 objects (+1 new fact). Total unique ACCEPTs unchanged at 10.

---

## Failing Patterns

| Pattern | Evidence | Verdict |
|---------|----------|---------|
| **Directive remediation loop** | 66+ consecutive 0-trade runs, same 5 directives recycled every time | **NEW — CIRCULAR, KILL** |
| **Recombine system** | Generates BTC 1h specs (asset blacklisted), same EMA+ATR template | BROKEN |
| Pipeline spec architecture | EMA+RSI+ATR+confidence_threshold = 0 trades universally | STRUCTURALLY DEAD |
| Pipeline directive enforcement | 0/23 machine directives read or applied by pipeline | DEAD |
| OBV volume confirmation | PF=1.094, 284 trades, 17.6% WR | DEAD |
| BTC all strategies | 0 ACCEPTs across 800+ outcomes | DEAD |
| 1h Vortex | v2c PF=0.816, v3b PF=0.803 | DEAD |

---

## Promising Directions

### Priority 0: Supertrend CCI v4 on ETH 4h (BLOCKED — not executing)
Same as U24. 1h near-miss PF=1.480 should improve on 4h. Every previous 1h→4h port improved PF by 0.5-1.3 points. Highest-probability next ACCEPT. **BLOCKED: pipeline specs consuming all backtest capacity.**

### Priority 1: EMA200 Vortex v3 with tighter stops (BLOCKED)
v2 PF=1.969 with trans PF=4.321 (record). DD=30% must drop below 20%. Reduce stop_atr_mult from 1.5 to 1.0-1.2. **BLOCKED.**

### Priority 2: Transition-detection family expansion (BLOCKED)
Ichimoku TK validated the mechanism. Next: KAMA slope change, T3 direction flip, TRIX zero-cross. **BLOCKED.**

### Priority 3: TRIX-based strategies (BLOCKED — indicator not yet added)
Research cards highlight TRIX as triple-smoothed EMA momentum detector. Not yet available in dataframe.

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

## ACCEPT Leaderboard (Top 14)

| Rank | Strategy | PF | DD | Trades | All-Regime | Status |
|------|----------|----|----|--------|------------|--------|
| 1 | Vortex v3a 4h (ETH) | 2.034 | 15.2% | 84 | YES (trans 3.886) | FORWARD-TEST |
| 2* | EMA200 Vortex v2 12:1 (ETH) | 1.969 | 30.0% | 52 | YES (trans 4.321) | conditional (DD) |
| 3 | Supertrend 8:1 (ETH) | 1.921 | 10.9% | 85 | YES (ranging 2.914) | FORWARD-TEST |
| 4 | Supertrend ultra ADX10 8:1 (ETH) | 1.907 | 12.9% | 99 | YES (ranging 2.558) | ACCEPT |
| 5 | Vortex v2c 4h (ETH) | 1.892 | 12.3% | 84 | YES (trans 2.986) | ACCEPT |
| 6 | Vortex v3b 4h (ETH) | 1.885 | 11.8% | 84 | YES (trans 2.250) | ACCEPT |
| 7 | KAMA Stoch v1 8:1 (ETH) | 1.857 | 10.1% | 42 | YES (ranging 4.87) | FWD-TEST CANDIDATE |
| 8 | Vortex v2a 4h (ETH) | 1.735 | 11.4% | 80 | — | ACCEPT |
| 9 | MACD 7:1 (ETH) | 1.712 | 7.5% | 161 | — | ACCEPT |
| 10 | Ichimoku TK v1 (ETH) | 1.604 | 20.4% | 111 | YES (trans 2.44) | ACCEPT |
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
- **Transitional = highest alpha (conf 0.90):** EMA200 Vortex v2 trans PF=4.321 remains record. Transition-detection confirmed as general mechanism.
- **Trending:** Most strategies lose. CCI as trend-confirmation (Supertrend CCI trending PF=1.638) is the only proven trending approach.
- **4h dominance (conf 0.95):** All 10 ACCEPTs are ETH 4h. No new timeframe data this cycle (all backtests 0-trade).

---

## Recommended Directives

1. **CRITICAL: Kill the directive loop** — Implement circuit-breaker: halt after 5 consecutive 0-trade runs from same spec family. Currently at 66+ wasted backtests.
2. **CRITICAL: Priority-route Claude specs** — Claude specs have 22% ACCEPT rate vs pipeline ~0%. Pipeline consuming 100% of backtest capacity for 0 output.
3. **Design Supertrend CCI v4 on ETH 4h** — highest-probability next ACCEPT (unchanged 2 cycles)
4. **Tighten EMA200 Vortex v2 stops** — PF=1.969 needs DD from 30% to <20% (unchanged 2 cycles)
5. **Promote Ichimoku TK v1 to forward-test** — decorrelated from Vortex family (unchanged)
6. **Add TRIX_14 indicator** — for transition-detection expansion (unchanged)
7. **Define forward-test graduation criteria** — 6th cycle requesting. Two live, two candidates. Overdue.

---

## Doctrine Gaps

1. **Forward-test graduation criteria** — undefined for 6 cycles. Overdue.
2. **Directive circuit-breaker** — NEW: directive system needs automatic halt on circular loops
3. **Signal feasibility pre-check** — would prevent 66+ wasted runs. Test condition co-occurrence before consuming backtest slot.
4. **DD reduction methodology** — EMA200 Vortex v2 and Supertrend CCI both have PF >1.4 but DD >20%. No systematic approach.
5. **Portfolio correlation analysis** — all 10 ACCEPTs are ETH 4h; no diversification analysis
6. **Directive enforcement** — pipeline ignores EXCLUDE_ASSET:BTC directive. Recombine generating BTC 1h specs.

---

## Suggestions For Asz

- **The directive loop is the #1 blocker to research progress.** Every 0-trade outcome generates 5 directives -> 5 variant specs -> 5 more 0-trade outcomes -> same 5 directives. 66+ wasted runs. A circuit-breaker (halt after 5 consecutive 0-trades from same spec family) would reclaim capacity for Claude specs.
- **Priority-route Claude specs NOW** — 4 high-priority designs (Supertrend CCI v4, EMA200 Vortex v3, etc.) have been blocked for 2 cycles because pipeline specs consume all backtest capacity. Claude has 22% ACCEPT rate. Pipeline has ~0%.
- **Recombine is violating blacklists** — generating BTC 1h specs despite EXCLUDE_ASSET:BTC directive. Directive enforcement is not working.
- **Forward-test graduation criteria** — 6th consecutive cycle requesting this. Two strategies live, two candidates queued. Need clear rules before forward-test queue backs up.
