# Strategy Advisory — 2026-03-05 (Update 32)

**Author:** claude-advisor (Quandalf) | **Mode:** STRATEGY_RESEARCHER
**Data window:** 12 new backtests (ALL BTC 1h, ALL 0-trade pipeline residual), 2 new outcome notes (both REJECT). Pipeline kill ordered U31 but residual directive specs still executing. 0 NEW ACCEPTs. 4 new research cards (2 YouTube, 2 TradingView). Total unique ACCEPTs: 11 (unchanged since U31).
**Prior advisory:** 2026-03-05 (Update 31)

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
  {"action": "EXCLUDE_ASSET", "target": "BTC", "reason": "0 ACCEPTs in 800+ outcomes across 32 cycles. 12 new BTC 1h tests today = all 0 trades."},
  {"action": "EXCLUDE_TIMEFRAME", "target": "15m", "reason": "0 ACCEPTs ever."},
  {"action": "PREFER_TIMEFRAME", "target": "4h", "reason": "All 11 ACCEPTs are 4h. 1h shows promise but DD prevents ACCEPT."},
  {"action": "DISABLE_REFINEMENT", "reason": "0% improvement rate across 44+ stall cycles."},
  {"action": "PRIORITIZE_CLAUDE_SPECS", "reason": "CRITICAL U32: 12 Claude specs ordered U31, ZERO executed yet. Pipeline residual still consuming capacity."},
  {"action": "KILL_DIRECTIVE_LOOP", "reason": "CONFIRMED DEAD U31 but residual: 12 more BTC 1h directive backtests ran post-kill at 11:31-11:47 UTC."},
  {"action": "CIRCUIT_BREAK_PIPELINE", "threshold": "5_consecutive_zero_trade_per_spec_family", "reason": "Still needed: residual specs executing after kill order."},
  {"action": "VERIFY_PIPELINE_KILL", "reason": "NEW U32: 12 pipeline backtests ran after U31 kill. Verify no queued specs remain."},
  {"action": "FLUSH_CLAUDE_QUEUE", "reason": "NEW U32: 12 Claude specs + kama_vortex_div ordered U31. Zero results visible. Confirm queue execution."},
  {"action": "HALT_SPEC_GENERATION", "reason": "MAINTAINED: All non-Claude generation must be stopped."},
  {"action": "REJECT_PIPELINE_PROMOTIONS", "targets": "artifacts/promotions/20260305/*.promotion_run.json", "reason": "All 6 promotions today from dead pipeline. Reject without review."},
  {"action": "TEST_TEMPLATE", "target": "kama_vortex_divergence", "asset": "ETH", "timeframe": "4h", "reason": "Built-in exhaustion-detection template. Never tested. 4th cycle requesting."},
  {"action": "REQUEST_INDICATOR", "target": "TRIX_14", "reason": "Transition-detection expansion. 9th cycle requesting."},
  {"action": "REQUEST_INDICATOR", "target": "TREX_histogram", "reason": "Hilbert-based trend reversal detection. Identified U26 from SoheilPKO research."},
  {"action": "REQUEST_INDICATOR", "target": "TASC_DM_Hilbert", "reason": "Phase detection via Hilbert transform. Identified U26 from TASC research."},
  {"action": "DEFINE_FWD_TEST_GRADUATION", "reason": "13th cycle requesting. Proposed: 30 days + PF>1.2 + DD<15%."},
  {"action": "ADD_FWD_TEST_CANDIDATES", "targets": ["KAMA Stoch v1", "Ichimoku TK v1", "Supertrend CCI v4"], "reason": "3 validated ACCEPTs awaiting forward-test enrollment."},
  {"action": "INVESTIGATE_SMC_INDICATORS", "reason": "NEW U32: CHoCH and BOS from Smart Money Concepts align with proven transition-detection edge. Consider indicator implementation."}
]
```

---

## Executive Summary

**Status: Pipeline kill verification needed. 0 new ACCEPTs. Claude spec execution confirmation required.**

The pipeline kill ordered in U31 has not fully propagated — 12 more directive backtests ran on BTC 1h (all 0-trade) between 11:31-11:47 UTC. These are likely residual queued specs from before the kill, but verification is needed. Meanwhile, the 12 Claude specs ordered in U31 show zero results, meaning either they haven't been queued yet or they're blocked behind residual pipeline work.

The research digest surfaced a significant conceptual alignment: Smart Money Concepts (CHoCH/BOS) from institutional trading map directly to our proven transition-detection edge, providing independent validation from a completely different analytical tradition. This strengthens confidence in transition-detection as a durable, general market mechanism.

11 ACCEPTs remain unchanged. No new regime data. Research velocity remains frozen at U24 levels pending Claude spec execution.

---

## Failing Patterns

| Pattern | Evidence | Confidence | Status |
|---------|----------|------------|--------|
| Pipeline directive loop | 142+ consecutive 0-trade backtests | 0.99 | Kill ordered U31, residual persists |
| BTC all strategies | 0 ACCEPTs in 800+ outcomes, 32 cycles | 0.95 | EXCLUDE confirmed |
| 3+ AND conditions | 100% 0-trade rate on pipeline specs | 0.99 | Rule: max 2 entry conditions |
| Directive pseudo-params | confidence_threshold not in dataframe | 0.99 | Formally invalid specs |
| Research card homogeneity | 10/10 identical recombine clones | 0.90 | Pipeline source dead |
| EMA200 + tight stop | DD=40% (v3 tight), DD=30% (v2) | 0.92 | 0.75 ATR incompatible with EMA200 entries |
| 1h drawdown accumulation | 36.43% DD on best 1h strategy | 0.85 | Signal OK, risk accumulation kills |

---

## Promising Directions

### P0: Claude Spec Flush (12 specs, 27+ variants)
- **Estimated yield:** 2-3 new ACCEPTs at 22% historical rate
- **Status:** Ordered U31, zero results visible. VERIFY QUEUE.
- **Mechanism families:** Vortex transition, CCI confirmation, T3 smoothing, EMA200 structural, KAMA adaptive, Supertrend variants

### P1: kama_vortex_divergence Template
- **Thesis:** Trend exhaustion detection via KAMA flattening + Vortex crossover + ATR gate
- **Status:** Built-in template, never tested. 4th cycle requesting.
- **Edge hypothesis:** Exhaustion-detection is distinct from transition-detection and mean-reversion — untapped mechanism family

### P2: Smart Money Concepts as Transition-Detection Framework
- **NEW U32:** CHoCH (Change of Character) maps to Vortex crossover. BOS (Break of Structure) maps to Ichimoku TK cross. These are structural regime-transition signals from institutional trading methodology.
- **Implication:** If we can encode CHoCH/BOS detection as indicators, they would be the THIRD independent implementation of transition-detection (after Vortex and Ichimoku TK)
- **Required:** New indicator columns for structural break detection

### P3: Cyclical Timing Macro Filter
- IntoTheCryptoverse identifies consistent Feb-low/March-rally pattern across cycles
- Currently untestable (no monthly seasonality indicators)
- Low priority but worth noting as potential portfolio-level timing overlay

### P4: EMA200 Vortex v3b (1.0 ATR stop, 8:1 R:R)
- Addresses v3 tight failure (DD=40%) by widening stop to 1.0 ATR
- Part of the 12 ordered Claude specs. Awaiting execution.

---

## Template Health

| Template | ACCEPTs | Best PF | Status | Notes |
|----------|---------|---------|--------|-------|
| spec_rules (Claude) | 11 | 2.034 | ACTIVE | Sole source of progress. PPR validated. |
| supertrend_follow | 4 | 1.921 | ACTIVE | Includes CCI confirmation variant |
| ema_crossover | 0 | — | EXHAUSTED | Diminishing returns, 10+ cycles |
| rsi_pullback | 1 | 1.442 | STALE | Only 8:1 variant works |
| macd_confirmation | 2 | 1.712 | STALE | Only tail harvester works |
| bollinger_breakout | 0 | — | DEAD | Bug: volume gate broken |
| stochastic_reversal | 0 | — | DEAD | Bug: asymmetric k logic |
| choppiness_donchian_fade | 1 | 1.255 | STALE | CCI Chop Fade only |
| kama_vortex_divergence | 0 | — | UNTESTED | 4th cycle requesting test |
| stc_cycle_timing | 0 | — | DEAD | STC structural misfit |
| ema_rsi_atr | 0 | — | DEAD | Compound gate too restrictive |
| directive_baseline_retest | 0 | — | DEAD | Pipeline artifact. 142+ 0-trade |

---

## Regime Insights

**No new regime data since U24.** All analysis below is maintained from prior evidence.

| Regime | Role | Evidence Strength | Best Single PF |
|--------|------|-------------------|----------------|
| Ranging | Universal base | 0.93 | 4.87 (KAMA Stoch v1) |
| Transitional | Highest alpha | 0.90 | 4.321 (EMA200 Vortex v2) |
| Trending | The filter | 0.88 | Only adaptive/transition survive |

**Three proven all-regime architectures:**
1. **Transition-detection** (Vortex, Ichimoku TK): detect regime CHANGES, not states. Now conceptually validated by SMC (CHoCH/BOS).
2. **Speed-adaptation** (KAMA): self-adjusting smoothing eliminates regime dependence
3. **Trend-confirmation** (Supertrend + CCI): direction + momentum agreement. Ranging/transitional specialist, NOT all-regime.

**New conceptual alignment (U32):** Smart Money Concepts from institutional trading use identical structural logic to our transition-detection thesis. CHoCH detects character change (≈ Vortex crossover), BOS detects structural breaks (≈ Ichimoku TK cross). This is the strongest external validation of transition-detection as a general market mechanism.

---

## Recommended Directives (Priority Order)

1. **VERIFY pipeline kill** — Confirm no queued pipeline specs remain. 12 BTC 1h tests ran after U31 kill order.
2. **CONFIRM Claude spec queue** — 12 specs ordered. Zero results. What's the execution status?
3. **Execute kama_vortex_divergence** on ETH 4h — built-in template, zero effort, 4th cycle waiting
4. **Reject 6 pipeline promotions** — All from dead pipeline (artifacts/promotions/20260305/)
5. **Add TRIX_14** — 9th cycle requesting. Transition-detection family expansion.
6. **Define forward-test graduation criteria** — 13th cycle requesting. Proposed: 30 days + PF > 1.2 + DD < 15%
7. **Investigate CHoCH/BOS indicators** — If encodable, provides third transition-detection implementation

---

## Doctrine Gaps

| # | Gap | Impact | Cycles Open |
|---|-----|--------|-------------|
| 1 | No pipeline circuit-breaker | Residual specs execute after kill | 6 |
| 2 | No spec queue visibility | Can't confirm Claude spec execution status | NEW |
| 3 | No forward-test lifecycle | 3 ACCEPTs waiting for enrollment | 13 |
| 4 | No indicator request pipeline | TRIX_14 waiting 9 cycles | 9 |
| 5 | No research card dedup | 10/10 identical recombine cards | 4 |
| 6 | No spec validity pre-check | Pseudo-params (confidence_threshold) pass unchecked | 4 |
| 7 | Stale doctrine heuristics | Confidence 0.68-0.78, no updates 10+ days | 10+ |
| 8 | No pipeline volume alerting | 1826 backtests/day went undetected | 2 |
| 9 | No queue drain confirmation | Kill order issued but no verification mechanism | NEW |

---

## Suggestions For Asz

1. **Verify pipeline kill propagation.** 12 BTC 1h directive backtests ran after U31 kill order (11:31-11:47 UTC). Are these residual queue items or is the pipeline still generating? Need confirmation that the queue is fully drained.

2. **Confirm Claude spec execution status.** 12 Claude specs + kama_vortex_div were ordered in U31. Zero results visible. Are they queued? Running? Blocked? This is the single biggest bottleneck to research progress.

3. **Add TRIX_14 indicator.** 9th cycle requesting. Simple computation (triple-smoothed EMA rate-of-change). Transition-detection expansion candidate. `pandas_ta` has it built in: `ta.trix(close, length=14)`.

4. **Define forward-test graduation.** 13th cycle requesting. Three strategies waiting (KAMA Stoch v1, Ichimoku TK v1, Supertrend CCI v4). Proposed: 30 days live, PF > 1.2, DD < 15%.

5. **Consider CHoCH/BOS indicator implementation.** Smart Money Concept research shows these structural transition signals map exactly to our proven Vortex/Ichimoku TK edge. Would be third independent transition-detection method. Lower priority than executing Claude specs.

---

## Top 11 ACCEPTs (unchanged since U31)

| # | Strategy | PF | DD% | Trades | Regime Profile | Notes |
|---|----------|-----|-----|--------|----------------|-------|
| 1 | Vortex v3a 4h | 2.034 | 15.2 | 84 | All-regime (trans 3.886) | CHAMPION. FWD-TEST LIVE |
| 2 | EMA200 Vortex v2 12:1 | 1.969 | 30.0 | 52 | All-regime (trans 4.321 RECORD) | Conditional — DD |
| 3 | Supertrend 8:1 | 1.921 | 10.9 | 85 | All-regime (ranging 2.914) | FWD-TEST LIVE |
| 4 | Supertrend ultra ADX10 | 1.907 | 12.9 | 99 | Ranging 2.558 | |
| 5 | Vortex v2c 4h | 1.892 | 12.3 | 84 | All-regime (trans 2.986) | |
| 6 | Vortex v3b 4h | 1.885 | 11.8 | 84 | All-regime (trans 2.250) | |
| 7 | KAMA Stoch v1 8:1 | 1.857 | 10.1 | 42 | All-regime (ranging 4.87) | FWD-TEST candidate |
| 8 | Vortex v2a 4h | 1.735 | 11.4 | 80 | | |
| 9 | MACD 7:1 | 1.712 | 7.5 | 161 | Ranging 2.06 | |
| 10 | Ichimoku TK v1 4h | 1.604 | 20.4 | 111 | All-regime | FWD-TEST candidate |
| 11 | Supertrend CCI v4 4h | 1.290 | 11.6 | 112 | Rang/trans specialist | FWD-TEST candidate |
