# Quandalf Latest Response

**Timestamp:** 2026-03-03 11:53:09 AEST
**Prompt:** Ask him this exactly:

“Quandalf, paste the exact forward-test config for MACD 7:1 tail harvester in strict JSON-ready form:

1. strategy_name
2. template_name
3. full entry_long array
4. full entry_s...
**Status:** COMPLETE

---

Here's the exact forward-test config for **MACD 7:1 Tail Harvester**, pulled directly from the canonical spec and validated backtest:

```json
{
  "strategy_name": "macd_tail_harvester_7to1_4h",
  "template_name": "spec_rules",

  "entry_long": [
    "MACDh_12_26_9 crosses_above 0",
    "close > EMA_50"
  ],

  "entry_short": [
    "MACDh_12_26_9 crosses_below 0",
    "close < EMA_50"
  ],

  "exit_rules": [
    "Exit when price hits stop loss at 1.0x ATR_14 from entry (adverse direction)",
    "Exit when price hits take profit at 7.0x ATR_14 from entry (favorable direction)",
    "No trailing stop. No time-based exit. Pure SL/TP mechanical exits only."
  ],

  "risk_policy": {
    "stop_type": "atr",
    "stop_atr_mult": 1.0,
    "tp_type": "atr",
    "tp_atr_mult": 7.0,
    "risk_per_trade_pct": 1.0,
    "max_drawdown_cap": 0.20
  },

  "execution_policy": {
    "entry_fill": "bar_close",
    "tie_break": "worst_case",
    "allow_reverse": true
  },

  "filters_constraints": [
    "no repaint",
    "bot-friendly",
    "chart timeframe only",
    "bar-close execution"
  ],

  "required_indicators": [
    "EMA_50",
    "MACDh_12_26_9",
    "ATR_14"
  ],

  "canonical_backtest": {
    "spec_path": "artifacts/strategy_specs/20260301/strategy-spec-20260301-claude-mc6r4w8n.strategy_spec.json",
    "backtest_path": "artifacts/backtests/20260301/hl_20260301_f29b2f2b.backtest_result.json",
    "variant_name": "macd_tail_harvester_7to1_4h",
    "asset": "ETH",
    "timeframe": "1h",
    "pf": 1.712,
    "trade_count": 161,
    "win_rate": 0.1988,
    "max_drawdown_pct": 21.29,
    "net_profit_pct": 31.60,
    "total_return_pct": 86.88,
    "regime_pf": {
      "trending": 1.677,
      "ranging": 2.062,
      "transitional": 1.308
    },
    "data_period": "2025-08-01 to 2026-02-26",
    "fee_model": "taker 4.5bps + 1.0bps slippage"
  }
}
```

**One flag:** The spec was *designed* targeting 4h, but the canonical backtest ran on **1h data** (dataset path confirms `ETH/1h/`). The variant name carries the `_4h` suffix from the spec's intent, not from the tested timeframe. Memory lists DD=7.5% but the actual backtest max_drawdown_pct is **21.29%** â€” that discrepancy may reflect a different metric or a different run. Forward-test should decide: run on 1h (where this PF=1.712 is validated) or 4h (the original design intent, untested at 7:1).