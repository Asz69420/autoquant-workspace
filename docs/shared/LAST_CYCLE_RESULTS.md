# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `supertrend_cci_v4_4h` + `ema200_vortex_v3_tight`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| supertrend_cci_v4_4h | ETH | 4h | 1.290 | 26.79% | 11.6304% | 24.5674% | 112 | 24.5674% | PASS |
| ema200_vortex_v3_tight | ETH | 4h | 1.365 | 9.70% | 40.0554% | 67.8696% | 134 | 67.8696% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| supertrend_cci_v4_4h | ETH | 4h | 0.562 | 1.989 | 2.777 |
| ema200_vortex_v3_tight | ETH | 4h | 1.292 | 1.453 | 1.230 |

## Gate Failures
- None.

## Critical Comparison
- `supertrend_cci_v4_4h` trades: **112** | avg PF: **1.290**
- `ema200_vortex_v3_tight` trades: **134** | avg PF: **1.365**
- Trade count difference: **-22**
