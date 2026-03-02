# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `vortex_transition_v3a` + `vortex_transition_v3b` + `vortex_transition_v2c_btc`
- Status: COMPLETE
- Assets tested: BTC, ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| vortex_transition_v3a | ETH | 4h | 2.034 | 20.24% | 15.2325% | 79.8700% | 84 | 79.8700% | PASS |
| vortex_transition_v3a | ETH | 1h | 0.753 | 12.20% | 22.1241% | -16.6915% | 123 | -16.6915% | PASS |
| vortex_transition_v3a | BTC | 4h | 0.743 | 19.17% | 19.3842% | -18.0724% | 120 | -18.0724% | PASS |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.00% | 0.7259% | -0.7259% | 1 | -0.7259% | PASS |
| vortex_transition_v3b | ETH | 4h | 1.885 | 25.00% | 11.7566% | 61.6194% | 84 | 61.6194% | PASS |
| vortex_transition_v3b | ETH | 1h | 0.841 | 17.50% | 17.2546% | -11.6369% | 120 | -11.6369% | PASS |
| vortex_transition_v3b | BTC | 4h | 0.840 | 22.03% | 19.2607% | -11.4438% | 118 | -11.4438% | PASS |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |
| vortex_transition_v2c_btc | ETH | 4h | 1.892 | 25.00% | 12.3346% | 62.5311% | 84 | 62.5311% | PASS |
| vortex_transition_v2c_btc | ETH | 1h | 0.856 | 17.50% | 19.4136% | -10.5015% | 120 | -10.5015% | PASS |
| vortex_transition_v2c_btc | BTC | 4h | 0.754 | 22.03% | 18.6793% | -16.6617% | 118 | -16.6617% | PASS |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| vortex_transition_v3a | ETH | 4h | 1.572 | 2.022 | 3.886 |
| vortex_transition_v3a | ETH | 1h | 0.973 | 0.875 | 0.203 |
| vortex_transition_v3a | BTC | 4h | 0.737 | 0.417 | 1.418 |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v3b | ETH | 4h | 1.726 | 1.954 | 2.250 |
| vortex_transition_v3b | ETH | 1h | 1.259 | 0.872 | 0.135 |
| vortex_transition_v3b | BTC | 4h | 0.647 | 0.664 | 1.560 |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v2c_btc | ETH | 4h | 1.636 | 1.855 | 2.986 |
| vortex_transition_v2c_btc | ETH | 1h | 1.283 | 0.892 | 0.134 |
| vortex_transition_v2c_btc | BTC | 4h | 0.690 | 0.577 | 1.217 |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- None.

## Critical Comparison
- `vortex_transition_v3a` trades: **328** | avg PF: **0.883**
- `vortex_transition_v3b` trades: **323** | avg PF: **0.891**
- Trade count difference: **+5**
