# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-02
**Thesis:** Mean reversion in ranging markets — simplified to 2 conditions. Testing if base signal generates enough trades before adding filters.

### Strategy Spec

name: chop_donchian_fade_v2
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "close <= DCL_20_20"
entry_short:
- "CHOP_14_1_100 > 50"
- "close >= DCU_20_20"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Test Matrix
- Assets: BTC, ETH
- Timeframes: 1h, 4h
- Initial capital: $10,000

### What to Report
Write to LAST_CYCLE_RESULTS.md:
- PF, win rate, max drawdown %, net profit %, total trades per asset/timeframe
- Regime breakdown if available
- Gate failures if any
- Total return on capital %
