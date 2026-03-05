# Strategy Advisory — 2026-03-06 (Update 33)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 7 new backtest results (ALL ETH 4h Claude specs — FIRST Claude spec execution since U31). 30 outcome notes (ALL 0-trade directive REJECT). 3 new Claude specs written (T3 Vortex, MACDh CHOP, ALMA CCI). **0 NEW ACCEPTs** but critical near-miss data. Total unique ACCEPTs: 11 (unchanged).
**Prior advisory:** 2026-03-05 (Update 32)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 33 cycles."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 11 ACCEPTs are 4h."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "MAINTAINED: Directive pipeline still generating 0-trade waste. 30 more REJECT outcomes today."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "Pipeline waste continues unabated."},
  {"action": "HALT_SPEC_GENERATION", "reason": "MAINTAINED: All non-Claude generation must be stopped."},
  {"action": "REJECT_PIPELINE_PROMOTIONS", "targets": "artifacts/promotions/20260306/*.promotion_run.json", "reason": "All promotions from dead pipeline. Reject without review."},
  {"action": "TUNE_KAMA_VORTEX_DIV", "reason": "NEW U33: Template generated 9 trades (1 short of min 10). Near-miss, NOT dead. Relax ATR gate or KAMA flattening threshold to increase signal frequency."},
  {"action": "CLOSE_EMA200_FAMILY", "reason": "NEW U33: v3b 8:1 DD=25.56%, v3b 10:1 DD=32.20%. Three generations of EMA200 Vortex all fail DD constraint. Mechanism fundamentally high-DD."},
  {"action": "QUEUE_NEW_CLAUDE_SPECS", "targets": ["strategy-spec-20260306-claude-t3vtx01", "strategy-spec-20260306-claude-mchtrn01", "strategy-spec-20260306-claude-almcci01"], "reason": "NEW U33: 3 novel transition-detection specs written. 7 variants total. Need immediate backtest execution."},
  {"action": "REQUEST_INDICATOR", "target": "TRIX_14", "reason": "Transition-detection expansion. 10th cycle requesting."},
  {"action": "DEFINE_FWD_TEST_GRADUATION", "reason": "14th cycle requesting. Proposed: 30 days + PF>1.2 + DD<15%."},
  {"action": "ADD_FWD_TEST_CANDIDATES", "targets": ["KAMA Stoch v1", "Ichimoku TK v1", "Supertrend CCI v4"], "reason": "3 validated ACCEPTs awaiting forward-test enrollment."},
  {"action": "INVESTIGATE_SMC_INDICATORS", "reason": "CHoCH and BOS from Smart Money Concepts align with proven transition-detection edge."}
]
```

---

## Executive Summary

**Status: First Claude spec results since U31. 0 new ACCEPTs but critical near-miss data on kama_vortex_div and EMA200 family closure.**

The backtest queue finally executed 7 Claude-ordered specs (all ETH 4h). Key results:

1. **kama_vortex_div generated 9 trades** — just 1 short of the 10-trade minimum gate. After 5 cycles of requesting, the template IS functional but signals are too rare. Parameter tuning (wider KAMA flattening threshold or lower ATR gate) should push it over the trade-count minimum.

2. **EMA200 Vortex family is CLOSED.** v3b (1.0 ATR stop) was the fix attempt for v3 tight (0.75 ATR, DD=40%) and v2 (DD=30%). Result: DD=25-32% across both R:R variants. Three generations prove EMA200 entries cluster at high-volatility transition points where stops get hit regardless of width. The mechanism amplifies transitional alpha (trans PF=2.297) but the DD cost is structural.

3. **Supertrend CCI 8:1 variant**: PF=1.358 (up from 1.290) but DD=25.36% (up from 11.63%). The 8:1 R:R helps per-trade but can't solve DD. Default 4h variant remains the ACCEPT.

4. **3 new Claude specs written** — T3 Vortex Transition, MACDh CHOP Transition, ALMA CCI Exhaustion. These represent novel mechanism tests awaiting execution.

---

## Failing Patterns

| Pattern | Evidence | Confidence | Status |
|---------|----------|------------|--------|
| Pipeline directive loop | 170+ consecutive 0-trade backtests | 0.99 | STILL ACTIVE despite kill order |
| EMA200 + any stop width | v2 DD=30%, v3 DD=40%, v3b DD=25-32% | 0.95 | CLOSED — 3 generations failed |
| BTC all strategies | 0 ACCEPTs in 800+ outcomes | 0.95 | EXCLUDE confirmed |
| 3+ AND conditions | 100% 0-trade rate | 0.99 | Rule: max 2 conditions |
| Supertrend CCI 8:1 R:R | PF up (1.358) but DD up (25.36%) | 0.85 | R:R improvement doesn't reduce DD |
| Research card homogeneity | 10/10 identical recombine clones | 0.90 | Pipeline source dead |

---

## Promising Directions

### P0: kama_vortex_div Parameter Tuning
- **9 trades in 5002 bars** — template works, signals just too rare
- Tuning options: relax KAMA flattening threshold, lower ATR gate, or widen Vortex crossover proximity window
- Combines two proven ACCEPT families (KAMA PF=1.857 + Vortex PF=2.034)
- Exhaustion-detection remains untested mechanism with highest theoretical potential

### P1: New Claude Specs (3 specs, 7 variants)
- **T3 Vortex Transition** (claude-t3vtx01): T3 smooth filter + Vortex cross. Tests if T3's near-zero-lag reduces false Vortex signals.
- **MACDh CHOP Transition** (claude-mchtrn01): MACD histogram zero-cross as 4th transition-detector + CHOP ranging gate. Novel use of MACDh.
- **ALMA CCI Exhaustion** (claude-almcci01): ALMA adaptive trend + CCI exhaustion from -100. Tests ALMA as KAMA alternative.
- **Expected yield:** 1-2 ACCEPTs at historical 24% rate across 7 variants

### P2: Supertrend CCI v4 Default Variant — Forward-Test Ready
- Default 4h variant (PF=1.290, DD=11.63%) is the existing ACCEPT
- 8:1 variant showed PF improvement but DD blowout — confirms default is optimal
- Ready for forward-test enrollment alongside Vortex v3a and Supertrend 8:1

### P3: SMC CHoCH/BOS Indicators
- Conceptual alignment with transition-detection confirmed (U32)
- Would be 3rd independent implementation if encodable
- Blocked on indicator implementation

---

## Template Health

| Template | ACCEPTs | Best PF | Status | Notes |
|----------|---------|---------|--------|-------|
| spec_rules (Claude) | 11 | 2.034 | ACTIVE | Sole source of progress |
| supertrend_follow | 4 | 1.921 | ACTIVE | CCI confirmation variant proven |
| kama_vortex_divergence | 0 | — | NEAR-MISS | 9 trades (1 short). Needs parameter tuning. |
| ema_crossover | 0 | — | EXHAUSTED | 10+ cycles |
| rsi_pullback | 1 | 1.442 | STALE | Only 8:1 variant works |
| macd_confirmation | 2 | 1.712 | STALE | Only tail harvester |
| choppiness_donchian_fade | 1 | 1.255 | STALE | CCI Chop Fade only |
| bollinger_breakout | 0 | — | DEAD | Bug: volume gate |
| stochastic_reversal | 0 | — | DEAD | Bug: asymmetric k |
| stc_cycle_timing | 0 | — | DEAD | STC structural misfit |
| ema_rsi_atr | 0 | — | DEAD | Compound gate |
| directive_baseline_retest | 0 | — | DEAD | 170+ 0-trade |

---

## Regime Insights

**NEW DATA: Supertrend CCI 8:1 variant regime breakdown confirms ranging/transitional specialization.**

| Regime | Role | Evidence Strength | Best Single PF |
|--------|------|-------------------|----------------|
| Ranging | Universal base | 0.93 | 4.87 (KAMA Stoch v1) |
| Transitional | Highest alpha | 0.90 | 4.321 (EMA200 Vortex v2) |
| Trending | The filter | 0.88 | Only adaptive/transition survive |

**EMA200 Vortex family regime data (NEW):**
- v3b 10:1: trending 0.574, ranging 1.751, transitional 2.297
- v3b 8:1: trending 0.417, ranging 1.505, transitional 1.476
- Pattern: EMA200 amplifies transitional alpha but trending is always negative — the EMA200 filter acts as a transition-detector that bleeds during non-transitional periods

**Supertrend CCI 8:1 regime data (NEW):**
- trending 0.742, ranging 1.548, transitional 3.291
- vs default: trending 0.562, ranging 1.989, transitional 2.777
- Pattern: 8:1 R:R shifts alpha toward transitional (fewer but bigger wins) while degrading ranging

**Three proven all-regime architectures** (unchanged):
1. Transition-detection (Vortex, Ichimoku TK)
2. Speed-adaptation (KAMA)
3. Trend-confirmation (Supertrend + CCI) — ranging/transitional specialist only

---

## Recommended Directives (Priority Order)

1. **Tune kama_vortex_div** — 9 trades is 1 short. Relax KAMA flattening threshold or ATR gate. This is the closest we've come to a new mechanism family (exhaustion-detection).
2. **Execute 3 new Claude specs** — T3 Vortex, MACDh CHOP, ALMA CCI (7 variants). Novel transition-detection candidates.
3. **Close EMA200 Vortex family** — 3 generations, all DD>20%. Stop allocating compute to this family.
4. **Add TRIX_14** — 10th cycle requesting. Transition-detection expansion.
5. **Define forward-test graduation** — 14th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15%.
6. **Reject pipeline promotions** — All from dead pipeline.

---

## Doctrine Gaps

| # | Gap | Impact | Cycles Open |
|---|-----|--------|-------------|
| 1 | No pipeline circuit-breaker | Residual specs execute after kill | 7 |
| 2 | No forward-test lifecycle | 3 ACCEPTs waiting for enrollment | 14 |
| 3 | No indicator request pipeline | TRIX_14 waiting 10 cycles | 10 |
| 4 | No research card dedup | 10/10 identical recombine cards | 5 |
| 5 | No spec validity pre-check | Pseudo-params pass unchecked | 5 |
| 6 | No template parameter tuning protocol | kama_vortex_div at 9/10 trades, no tuning path | NEW |
| 7 | Stale doctrine heuristics | Confidence 0.68-0.78, no updates 10+ days | 11+ |

---

## Suggestions For Asz

1. **Tune kama_vortex_div template parameters.** The template generated 9 trades — 1 short of the 10-trade minimum. The exhaustion-detection mechanism WORKS but is too selective. Options: lower `atr_gate` threshold in `signal_templates.py`, widen KAMA flattening window, or relax Vortex crossover proximity. This is the most promising path to a genuinely new mechanism family.

2. **Queue 3 new Claude specs for backtest.** T3 Vortex (claude-t3vtx01), MACDh CHOP (claude-mchtrn01), ALMA CCI (claude-almcci01) — 7 variants total. All follow brain rules (2 conditions, ETH 4h, 8:1+ R:R). Files are in `artifacts/strategy_specs/20260306/`.

3. **Close the EMA200 Vortex family.** Three generations (v2, v3, v3b) all exceed 20% DD. The mechanism amplifies transitional alpha but the DD cost is structural — EMA200 entries cluster at high-volatility transition points. No further compute on this family.

4. **Add TRIX_14.** 10th cycle requesting. `pandas_ta.trix(close, length=14)`. Last untapped transition-detection indicator.

5. **Define forward-test graduation criteria.** 14th cycle requesting. Three ACCEPTs ready (KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4). Proposed: 30 days live, PF > 1.2, DD < 15%.

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
