# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `vortex_transition_v1` + `kama_vortex_trend_v1`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| vortex_transition_v1 | ETH | 4h | 1.385 | 27.85% | 10.1689% | 19.8002% | 79 | 19.8002% | PASS |
| vortex_transition_v1 | ETH | 1h | 0.985 | 21.37% | 13.1992% | -1.1487% | 117 | -1.1487% | PASS |
| kama_vortex_trend_v1 | ETH | 4h | 1.122 | 27.71% | 30.2894% | 24.8993% | 332 | 24.8993% | PASS |
| kama_vortex_trend_v1 | ETH | 1h | 0.934 | 25.06% | 49.5779% | -14.2397% | 391 | -14.2397% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| vortex_transition_v1 | ETH | 4h | 1.453 | 1.222 | 1.613 |
| vortex_transition_v1 | ETH | 1h | 1.388 | 0.804 | 0.419 |
| kama_vortex_trend_v1 | ETH | 4h | 1.248 | 0.943 | 1.528 |
| kama_vortex_trend_v1 | ETH | 1h | 0.685 | 1.341 | 0.797 |

## Gate Failures
- None.

## Critical Comparison
- `vortex_transition_v1` trades: **196** | avg PF: **1.185**
- `kama_vortex_trend_v1` trades: **723** | avg PF: **1.028**
- Trade count difference: **-527**
