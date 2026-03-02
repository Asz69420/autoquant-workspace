# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-03
**Thesis:** Oscillator mean-reversion exhausted (CCI best at 1.255, QQE dead, STC breakeven). But STC/CCI both show transitional PF >1.2. New thesis: catch range-to-trend transitions using Vortex crossovers. First-ever test of VTXP/VTXM.

### Strategy 1: Vortex Transition Breakout v1

**Hypothesis:** VTXP crossing above VTXM detects trend initiation. Gating with CHOP < 50 (market leaving range) isolates transition moments. Ride the new trend with wide R:R.

name: vortex_transition_v1
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "CHOP_14_1_100 < 50"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Strategy 2: KAMA Vortex Trend v1

**Hypothesis:** KAMA adapts speed to volatility — flat in ranges, responsive in trends. KAMA slope confirming Vortex direction = higher-quality transition entry. Tests two untested indicators together.

name: kama_vortex_trend_v1
template_name: spec_rules
entry_long:
- "VTXP_14 > VTXM_14"
- "close > KAMA_10_2_30"
entry_short:
- "VTXM_14 > VTXP_14"
- "close < KAMA_10_2_30"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix
- Assets: ETH only
- Timeframes: 4h, 1h
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades
- Regime breakdown (trending/ranging/transitional PF)
- **Critical:** Which regime dominates? Expecting transitional.
