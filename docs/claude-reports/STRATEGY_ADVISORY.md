# Strategy Advisory — 2026-03-06 (Update 34)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 131 new backtests in 20260306 (ALL zero-trade directive pipeline). 0 new Claude spec results (3 specs from U33 STILL pending — 2nd cycle blocked). 7 new research cards (2 directly relevant to transition-detection). **0 NEW ACCEPTs.** Total unique ACCEPTs: 11 (unchanged).
**Prior advisory:** 2026-03-06 (Update 33)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 930+ outcomes across 34 cycles."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 11 ACCEPTs are 4h."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "CRITICAL: 131 more zero-trade backtests today. Kill order has had ZERO effect. Pipeline fully self-regenerating."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "300+ zero-trade backtests since kill order. No circuit-breaker exists."},
  {"action": "HALT_SPEC_GENERATION", "reason": "MAINTAINED: All non-Claude generation must be stopped. Pipeline producing 4 new specs, 6 feasibility, 3 promotions, 3 batches, 3 theses TODAY despite kill."},
  {"action": "REJECT_PIPELINE_PROMOTIONS", "targets": "artifacts/promotions/20260306/*.promotion_run.json", "reason": "3 new promotions from dead pipeline today."},
  {"action": "DRAIN_BACKTEST_QUEUE", "reason": "NEW U34: Claude specs blocked 2 cycles. Directive waste consumes all queue slots. Must drain before any Claude spec can execute."},
  {"action": "QUEUE_PRIORITY_SYSTEM", "reason": "NEW U34: Claude specs should execute before directive pipeline specs. Current FIFO allows 131 zero-trade specs to block 7 valuable variants."},
  {"action": "TUNE_KAMA_VORTEX_DIV", "reason": "UPDATED U34: 0/9 WR (not near-miss). Needs parameter tuning to increase trade count to 20+ FIRST, then evaluate edge."},
  {"action": "CLOSE_EMA200_FAMILY", "reason": "MAINTAINED: 3 generations, all DD>20%. Family structurally closed."},
  {"action": "QUEUE_NEW_CLAUDE_SPECS", "targets": ["strategy-spec-20260306-claude-t3vtx01", "strategy-spec-20260306-claude-mchtrn01", "strategy-spec-20260306-claude-almcci01"], "reason": "BLOCKED 2 CYCLES: 7 variants awaiting execution. Expected 1-2 ACCEPTs."},
  {"action": "REQUEST_INDICATOR", "target": "TRIX_14", "reason": "Transition-detection expansion. 11th cycle requesting."},
  {"action": "DEFINE_FWD_TEST_GRADUATION", "reason": "15th cycle requesting. Proposed: 30 days + PF>1.2 + DD<15%."},
  {"action": "ADD_FWD_TEST_CANDIDATES", "targets": ["KAMA Stoch v1", "Ichimoku TK v1", "Supertrend CCI v4"], "reason": "3 validated ACCEPTs awaiting forward-test enrollment."},
  {"action": "INVESTIGATE_REGIME_DETECTION", "reason": "NEW U34: 5 independent frameworks converge on transition-detection. Research cards (VIX-VIXEQ, Euphoria) add 2 more validation sources."}
]
```

---

## Executive Summary

**Status: Pipeline kill completely ineffective — 131 more zero-trade backtests today. Claude specs blocked 2nd consecutive cycle. Research convergence strengthens transition-detection thesis to 5 independent frameworks.**

1. **Pipeline self-regeneration continues unabated.** 131 new backtests in 20260306, ALL zero-trade, ALL BTC 1h directive specs. Additionally: 4 new strategy specs, 6 feasibility reports, 3 batch backtests, 3 promotion runs, 3 thesis files — ALL from the dead pipeline. The kill order from U31 has had ZERO effect across 3 cycles. The system has no circuit-breaker and no queue drain mechanism.

2. **3 Claude specs from U33 still pending.** T3 Vortex, MACDh CHOP, and ALMA CCI have produced zero backtest results for the 2nd consecutive cycle. The backtest queue is consumed entirely by directive pipeline specs, starving Claude specs of compute. This is the most critical blocker — every blocked cycle delays ~2 potential ACCEPTs.

3. **kama_vortex_div reassessment.** The U33 "near-miss" label was premature. The template generated 9 trades but ALL 9 LOST (0% WR, PF=0.000). While 9 trades is too small to conclude the mechanism has no edge (at 10:1 R:R, 9.1% WR breaks even, P(0/9 | true WR=11%) = 0.35), the result is not encouraging. Priority: parameter tuning to increase trade count FIRST, then evaluate edge quality.

4. **Research convergence on regime detection.** New research cards bring the total to 5+ independent frameworks supporting transition-detection as general edge: (1) Vortex — validated PF=2.034, (2) Ichimoku TK — validated PF=1.604, (3) SMC CHoCH/BOS — conceptual, (4) VIX-VIXEQ Regime Detector — new research card, (5) Euphoria/exhaustion detection — new research card. This convergence strengthens confidence from hypothesis to near-established principle.

---

## Failing Patterns

| Pattern | Evidence | Confidence | Status |
|---------|----------|------------|--------|
| Pipeline self-regeneration | 131 more zero-trade today (300+ since kill) | 0.99 | CRITICAL — no circuit-breaker |
| Claude spec queue starvation | 0 results for 2nd cycle, directives consume all slots | 0.99 | BLOCKING ALL PROGRESS |
| EMA200 + any stop width | v2 DD=30%, v3 DD=40%, v3b DD=25-32% | 0.95 | CLOSED — 3 generations failed |
| BTC all strategies | 0 ACCEPTs in 930+ outcomes | 0.95 | EXCLUDE confirmed |
| 3+ AND conditions | 100% 0-trade rate | 0.99 | Rule: max 2 conditions |
| kama_vortex_div 0/9 WR | 0% WR on 9 trades (low sample) | 0.65 | INCONCLUSIVE — needs more trades |
| Research card homogeneity | 10/10 identical recombine clones (prev cycles) | 0.90 | Pipeline source dead |

---

## Promising Directions

### P0: Execute Pending Claude Specs (CRITICAL BLOCKER)
- 3 specs blocked 2 cycles: T3 Vortex (claude-t3vtx01), MACDh CHOP (claude-mchtrn01), ALMA CCI (claude-almcci01)
- 7 variants total — expected yield 1-2 ACCEPTs at historical 24% rate
- Backtest queue must be CLEARED of directive specs before Claude specs can execute
- This is the #1 priority — every blocked cycle costs ~2 potential ACCEPTs

### P1: Regime Detection Research Convergence
- 5 independent frameworks now support transition-detection as general edge
- NEW: VIX-VIXEQ Regime Detector concept — comparing realized vs expected volatility to detect regime shifts. We have ATR (realized) but need implied volatility proxy.
- NEW: Euphoria Indicator — momentum exhaustion via extreme sentiment zones. Maps to CCI/RSI extremes + momentum divergence.
- NEW: Smart Pivot Reversals / GuarDeer SMC — reinforces CHoCH/BOS from U32. Two more independent SMC implementations.
- Next step: design strategy spec combining transition-detection with exhaustion confirmation

### P2: kama_vortex_div Parameter Tuning
- Template IS mechanically functional (generates 9 trades over 5002 bars)
- BUT 0/9 WR means edge quality is unknown — need 20+ trades to evaluate
- Parameter tuning to increase trade count: relax KAMA flattening threshold, lower ATR gate
- Combines two proven families (KAMA + Vortex) — theoretical support strong
- Priority: trade count first, edge evaluation second

### P3: Forward-Test Enrollment
- 3 ACCEPTs ready: KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4
- Graduation criteria still undefined (15th cycle requesting)

---

## Template Health

| Template | ACCEPTs | Best PF | Status | Notes |
|----------|---------|---------|--------|-------|
| spec_rules (Claude) | 11 | 2.034 | ACTIVE | Sole source of progress |
| supertrend_follow | 4 | 1.921 | ACTIVE | CCI confirmation variant proven |
| kama_vortex_divergence | 0 | — | INCONCLUSIVE | 9 trades, 0% WR. Needs parameter tuning. |
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

**No new regime data this cycle** — all 131 backtests are zero-trade. Regime insights unchanged from U33.

**Research convergence meta-pattern:** 5 independent frameworks (Vortex, Ichimoku TK, SMC, VIX-VIXEQ, Euphoria) all point to regime transition detection as the general edge mechanism. This is no longer a hypothesis — it's a meta-pattern supported by:
- 2 validated strategies (Vortex PF=2.034, Ichimoku TK PF=1.604)
- 3 conceptual frameworks from independent research sources
- Every all-regime ACCEPT uses some form of regime-adaptive or transition-detecting mechanism

**Three proven all-regime architectures** (unchanged):
1. Transition-detection (Vortex, Ichimoku TK)
2. Speed-adaptation (KAMA)
3. Trend-confirmation (Supertrend + CCI) — ranging/transitional specialist only

| Regime | Role | Evidence Strength | Best Single PF |
|--------|------|-------------------|----------------|
| Ranging | Universal base | 0.93 | 4.87 (KAMA Stoch v1) |
| Transitional | Highest alpha | 0.90 | 4.321 (EMA200 Vortex v2) |
| Trending | The filter | 0.88 | Only adaptive/transition survive |

---

## Recommended Directives (Priority Order)

1. **DRAIN BACKTEST QUEUE** — Clear all directive pipeline specs from the queue. Claude specs cannot execute while directive waste consumes all slots. This is the #1 blocker.
2. **Execute 3 pending Claude specs** — T3 Vortex, MACDh CHOP, ALMA CCI (7 variants). Blocked 2 cycles.
3. **Tune kama_vortex_div parameters** — Increase trade count to 20+ first (relax KAMA flattening threshold or ATR gate), then evaluate edge.
4. **Add TRIX_14** — 11th cycle requesting. `pandas_ta.trix(close, length=14)`. Transition-detection expansion.
5. **Define forward-test graduation** — 15th cycle requesting. 3 ACCEPTs waiting.
6. **Reject all pipeline promotions** — 3 new promotions from dead pipeline today.

---

## Doctrine Gaps

| # | Gap | Impact | Cycles Open |
|---|-----|--------|-------------|
| 1 | No pipeline circuit-breaker | 131 more zero-trade today despite kill | 8 |
| 2 | No backtest queue drain mechanism | Claude specs blocked 2 cycles by directive waste | NEW |
| 3 | No forward-test lifecycle | 3 ACCEPTs waiting for enrollment | 15 |
| 4 | No indicator request pipeline | TRIX_14 waiting 11 cycles | 11 |
| 5 | No research card dedup | Identical recombine clones | 6 |
| 6 | No spec validity pre-check | Pseudo-params pass unchecked | 6 |
| 7 | No template parameter tuning protocol | kama_vortex_div at 9 trades, no tuning path | 2 |
| 8 | Stale doctrine heuristics | Confidence 0.68-0.78, no updates 12+ days | 12+ |
| 9 | No queue priority system | 131 zero-trade specs execute before 7 Claude variants | NEW |

---

## Suggestions For Asz

1. **URGENT: Drain the backtest queue.** 131 zero-trade directive specs ran today. The kill order from U31 has had zero effect — the pipeline is fully self-regenerating (4 new specs, 6 feasibility, 3 promotions, 3 batches, 3 theses generated TODAY). 3 Claude specs have produced ZERO results for 2 cycles because directive waste consumes all queue slots. Nothing else matters until Claude specs can execute.

2. **Implement queue priority.** Claude specs should execute before directive pipeline specs. Current FIFO allows 131 zero-trade specs to block 7 valuable variants. A simple priority flag (source=claude vs source=pipeline) would prevent this starvation pattern permanently.

3. **Add TRIX_14.** 11th cycle requesting. `pandas_ta.trix(close, length=14)`. Last untapped transition-detection indicator in pandas_ta.

4. **Define forward-test graduation criteria.** 15th cycle requesting. Three ACCEPTs ready (KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4). Proposed: 30 days live, PF > 1.2, DD < 15%.

5. **Tune kama_vortex_div in signal_templates.py.** 0/9 WR with low sample — edge is inconclusive, not dead. Relax KAMA flattening threshold and/or lower ATR gate to increase trade count to 20+, then re-evaluate.

---

## Top 11 ACCEPTs (unchanged)

| # | Strategy | PF | DD% | Trades | Regime Profile | Notes |
|---|----------|-----|-----|--------|----------------|-------|
| 1 | Vortex v3a 4h | 2.034 | 15.2 | 84 | All-regime (trans 3.886) | CHAMPION. FWD-TEST LIVE |
| 2 | EMA200 Vortex v2 12:1 | 1.969 | 30.0 | 52 | All-regime (trans 4.321 RECORD) | Conditional — DD. FAMILY CLOSED |
| 3 | Supertrend 8:1 | 1.921 | 10.9 | 85 | All-regime (ranging 2.914) | FWD-TEST LIVE |
| 4 | Supertrend ultra ADX10 | 1.907 | 12.9 | 99 | Ranging 2.558 | |
| 5 | Vortex v2c 4h | 1.892 | 12.3 | 84 | All-regime (trans 2.986) | |
| 6 | Vortex v3b 4h | 1.885 | 11.8 | 84 | All-regime (trans 2.250) | |
| 7 | KAMA Stoch v1 8:1 | 1.857 | 10.1 | 42 | All-regime (ranging 4.87) | FWD-TEST candidate |
| 8 | Vortex v2a 4h | 1.735 | 11.4 | 80 | | |
| 9 | MACD 7:1 | 1.712 | 7.5 | 161 | Ranging 2.06 | |
| 10 | Ichimoku TK v1 4h | 1.604 | 20.4 | 111 | All-regime | FWD-TEST candidate |
| 11 | Supertrend CCI v4 4h | 1.290 | 11.6 | 112 | Rang/trans specialist | FWD-TEST candidate |
