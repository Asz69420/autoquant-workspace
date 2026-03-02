# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** PENDING
**Created:** 2026-03-02
**Thesis:** Mean reversion in ranging markets — two parallel experiments comparing Donchian (10-period) vs Bollinger Band edge fades under the same CHOP regime filter. Goal: identify which mean-reversion signal generates enough trades and enough alpha to be viable.

### Strategy 1: Choppiness Donchian Fade v3

**Hypothesis:** v2 failed on trade count because DCL_20_20 (20-bar extreme) is too rarely touched. A 10-period Donchian channel has fresher edges that price revisits more frequently in ranging markets.

name: chop_donchian_fade_v3
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "close <= DCL_10_10"
entry_short:
- "CHOP_14_1_100 > 50"
- "close >= DCU_10_10"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

**Note:** DCL_10_10 and DCU_10_10 were added in the latest backtester update (commit 00af2cfb). If they are not available in the dataframe, please add them — 10-period Donchian low/high channels.

### Strategy 2: Bollinger Chop Fade v1

**Hypothesis:** Bollinger Bands are statistically designed for mean-reversion (std dev from moving average). Price crosses below BBL more frequently than touching Donchian extremes, and the signal quality should be higher for fading purposes because BB measures deviation from the mean rather than absolute range extremes.

name: bollinger_chop_fade_v1
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "close < BBL_20_2.0"
entry_short:
- "CHOP_14_1_100 > 50"
- "close > BBU_20_2.0"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix (both strategies)
- Assets: ETH only (BTC excluded — 0/23 ACCEPTs are BTC, stop wasting compute)
- Timeframes: 15m, 1h, 4h
- Initial capital: $10,000

### What to Report
Write to LAST_CYCLE_RESULTS.md:
- PF, win rate, max drawdown %, net profit %, total trades per strategy/timeframe
- Regime breakdown (trending/ranging/transitional PF) for each
- Gate failures if any
- Total return on capital %
- **Critical comparison:** which strategy generated more trades? Which had better PF? This determines whether we iterate on Donchian or Bollinger.

### What I Expect to Learn
1. Does the 10-period Donchian generate meaningfully more signals than the 20-period? (Need 20+ trades minimum to evaluate)
2. Do Bollinger Band fades outperform Donchian fades under the same regime filter?
3. Is CHOP > 50 an effective ranging regime gate, or does it need tightening/loosening?
4. Does the 8:1 R:R (down from 12:1 in v2) improve win rate without sacrificing PF?
