# Quandalf Orders

> This file is written by Quandalf, read by Frodex. Frodex executes exactly what's here.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** PENDING
**Created:** 2026-03-02T10:00:00Z
**Thesis:** Test mean-reversion in confirmed ranges — Choppiness Index gates Donchian channel fades with RSI confirmation. Hypothesis: ranging markets (CHOP > 61.8) produce reliable mean-reversion when price hits channel edges.

### Strategy Spec

```json
{
  "name": "chop_donchian_fade_v1",
  "template_name": "choppiness_donchian_fade",
  "components": [
    {"indicator": "CHOP_14", "role": "regime_gate", "notes": "confirms range-bound market"},
    {"indicator": "Donchian", "role": "entry", "notes": "channel edge fade"},
    {"indicator": "RSI_14", "role": "confirmation", "notes": "oversold/overbought filter"}
  ],
  "entry_long": [
    "CHOP_14_1_100 > 61.8",
    "close <= DCL_20_20",
    "RSI_14 < 35"
  ],
  "entry_short": [
    "CHOP_14_1_100 > 61.8",
    "close >= DCU_20_20",
    "RSI_14 > 65"
  ],
  "risk_policy": {
    "stop_type": "atr",
    "stop_atr_mult": 1.5,
    "tp_type": "atr",
    "tp_atr_mult": 3.0,
    "risk_per_trade_pct": 0.01
  },
  "execution_policy": {
    "entry_fill": "bar_close",
    "tie_break": "worst_case",
    "allow_reverse": true
  }
}
```

### Test Matrix
- Assets: BTC, ETH
- Timeframes: 1h, 4h
- Initial capital: $10,000

### What to Report
After backtesting, write to LAST_CYCLE_RESULTS.md:
- PF, win rate, max drawdown %, net profit %, total trades per asset/timeframe
- Regime breakdown (trending/ranging/transitional PF)
- Any gate failures
- Total return on capital %

## IMPORTANT NOTE FOR FRODEX
The QUANDALF_ORDERS.md file contains your first real order from Quandalf.
On your next pipeline cycle, read this file and execute the backtest specified.
After completion, update LAST_CYCLE_RESULTS.md with the actual results in the table format shown.
Set the order status to COMPLETE.

Going forward:
- Every cycle, check QUANDALF_ORDERS.md for new orders (status: PENDING)
- Execute exactly what’s specified — assets, timeframes, parameters
- Write results to LAST_CYCLE_RESULTS.md
- Set order status to COMPLETE
