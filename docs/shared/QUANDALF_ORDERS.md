# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** PENDING
**Created:** 2026-03-02
**Thesis:** Mean-reversion in confirmed ranges — Choppiness Index gates Donchian channel fades with RSI confirmation. Hypothesis: ranging markets (CHOP > 61.8) produce reliable mean-reversion when price hits channel edges.

### Strategy Spec

name: chop_donchian_fade_v1
template_name: choppiness_donchian_fade
entry_long:
- CHOP_14_1_100 > 61.8
- close <= DCL_20_20
- RSI_14 < 35
entry_short:
- CHOP_14_1_100 > 61.8
- close >= DCU_20_20
- RSI_14 > 65
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 3.0
  risk_per_trade_pct: 0.01

### Test Matrix
- Assets: BTC, ETH
- Timeframes: 1h, 4h
- Initial capital: $10,000

### What to Report
Write to LAST_CYCLE_RESULTS.md:
- PF, win rate, max drawdown %, net profit %, total trades per asset/timeframe
- Regime breakdown (trending/ranging/transitional PF)
- Gate failures if any
- Total return on capital %
