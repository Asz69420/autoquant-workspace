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
| vortex_transition_v3a | ETH | 4h | 1.959 | 20.00% | 15.3663% | 77.5872% | 85 | 77.5872% | PASS |
| vortex_transition_v3a | ETH | 1h | 0.720 | 11.81% | 22.1241% | -19.8714% | 127 | -19.8714% | PASS |
| vortex_transition_v3a | BTC | 4h | 0.724 | 18.85% | 21.2885% | -19.9497% | 122 | -19.9497% | PASS |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.00% | 0.7259% | -0.7259% | 1 | -0.7259% | PASS |
| vortex_transition_v3b | ETH | 4h | 1.861 | 25.00% | 11.8583% | 61.2660% | 84 | 61.2660% | PASS |
| vortex_transition_v3b | ETH | 1h | 0.803 | 16.94% | 17.2546% | -15.1268% | 124 | -15.1268% | PASS |
| vortex_transition_v3b | BTC | 4h | 0.817 | 21.67% | 21.2812% | -13.4556% | 120 | -13.4556% | PASS |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |
| vortex_transition_v2c_btc | ETH | 4h | 1.868 | 25.00% | 12.4413% | 62.1757% | 84 | 62.1757% | PASS |
| vortex_transition_v2c_btc | ETH | 1h | 0.816 | 16.94% | 19.4136% | -14.0363% | 124 | -14.0363% | PASS |
| vortex_transition_v2c_btc | BTC | 4h | 0.733 | 21.67% | 20.5808% | -18.5550% | 120 | -18.5550% | PASS |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| vortex_transition_v3a | ETH | 4h | 1.491 | 2.023 | 3.497 |
| vortex_transition_v3a | ETH | 1h | 0.926 | 0.837 | 0.195 |
| vortex_transition_v3a | BTC | 4h | 0.756 | 0.499 | 1.109 |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v3b | ETH | 4h | 1.637 | 2.089 | 2.013 |
| vortex_transition_v3b | ETH | 1h | 1.206 | 0.828 | 0.129 |
| vortex_transition_v3b | BTC | 4h | 0.654 | 0.713 | 1.313 |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v2c_btc | ETH | 4h | 1.552 | 1.982 | 2.670 |
| vortex_transition_v2c_btc | ETH | 1h | 1.228 | 0.846 | 0.128 |
| vortex_transition_v2c_btc | BTC | 4h | 0.699 | 0.632 | 0.985 |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- None.

## Critical Comparison
- `vortex_transition_v3a` trades: **335** | avg PF: **0.851**
- `vortex_transition_v3b` trades: **329** | avg PF: **0.870**
- Trade count difference: **+6**
