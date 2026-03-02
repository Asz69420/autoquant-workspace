# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `vortex_transition_v2a` + `vortex_transition_v2b` + `vortex_transition_v2c`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| vortex_transition_v2a | ETH | 4h | 1.735 | 25.00% | 11.4103% | 46.3597% | 80 | 46.3597% | PASS |
| vortex_transition_v2a | ETH | 1h | 1.128 | 17.50% | 19.4136% | 10.5625% | 120 | 10.5625% | PASS |
| vortex_transition_v2b | ETH | 4h | 1.436 | 26.25% | 11.7025% | 24.8972% | 80 | 24.8972% | PASS |
| vortex_transition_v2b | ETH | 1h | 1.080 | 20.51% | 12.4783% | 6.8898% | 117 | 6.8898% | PASS |
| vortex_transition_v2c | ETH | 4h | 1.892 | 25.00% | 12.3346% | 62.5311% | 84 | 62.5311% | PASS |
| vortex_transition_v2c | ETH | 1h | 0.856 | 17.50% | 19.4136% | -10.5015% | 120 | -10.5015% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| vortex_transition_v2a | ETH | 4h | 1.768 | 1.544 | 2.220 |
| vortex_transition_v2a | ETH | 1h | 1.812 | 1.031 | 0.133 |
| vortex_transition_v2b | ETH | 4h | 1.582 | 1.338 | 1.286 |
| vortex_transition_v2b | ETH | 1h | 1.529 | 0.886 | 0.439 |
| vortex_transition_v2c | ETH | 4h | 1.636 | 1.855 | 2.986 |
| vortex_transition_v2c | ETH | 1h | 1.283 | 0.892 | 0.134 |

## Gate Failures
- None.

## Critical Comparison
- `vortex_transition_v2a` trades: **200** | avg PF: **1.431**
- `vortex_transition_v2b` trades: **197** | avg PF: **1.258**
- Trade count difference: **+3**
