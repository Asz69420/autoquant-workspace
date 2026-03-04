# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `ichimoku_tk_transition_v1` + `cci_chop_fade_v3` + `supertrend_obv_confirm_v1` + `vortex_transition_v3a` + `vortex_transition_v3b` + `vortex_transition_v2c_btc`
- Status: COMPLETE
- Assets tested: BTC, ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ichimoku_tk_transition_v1 | ETH | 4h | 1.604 | 17.12% | 20.3841% | 61.1365% | 111 | 61.1365% | PASS |
| ichimoku_tk_transition_v1 | ETH | 1h | 0.556 | 14.63% | 32.0639% | -31.5347% | 123 | -31.5347% | PASS |
| ichimoku_tk_transition_v1 | BTC | 4h | 1.244 | 19.61% | 10.6584% | 22.3534% | 102 | 22.3534% | PASS |
| ichimoku_tk_transition_v1 | BTC | 1h | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | PASS |
| cci_chop_fade_v3 | ETH | 4h | 1.266 | 37.91% | 14.9253% | 28.3724% | 182 | 28.3724% | PASS |
| cci_chop_fade_v3 | ETH | 1h | 0.780 | 17.36% | 45.1494% | -25.8908% | 144 | -25.8908% | PASS |
| cci_chop_fade_v3 | BTC | 4h | 1.166 | 18.26% | 23.8901% | 16.0366% | 115 | 16.0366% | PASS |
| cci_chop_fade_v3 | BTC | 1h | 0.000 | 0.00% | 1.1702% | -1.1702% | 1 | -1.1702% | PASS |
| supertrend_obv_confirm_v1 | ETH | 4h | 1.094 | 17.61% | 26.7782% | 26.0788% | 284 | 26.0788% | PASS |
| supertrend_obv_confirm_v1 | ETH | 1h | 1.003 | 17.59% | 73.6259% | 0.8861% | 324 | 0.8861% | PASS |
| supertrend_obv_confirm_v1 | BTC | 4h | 0.878 | 20.28% | 39.9556% | -24.4313% | 281 | -24.4313% | PASS |
| supertrend_obv_confirm_v1 | BTC | 1h | 0.000 | 0.00% | 2.6445% | -2.6445% | 3 | -2.6445% | PASS |
| vortex_transition_v3a | ETH | 4h | 1.958 | 20.00% | 15.3615% | 77.5317% | 85 | 77.5317% | PASS |
| vortex_transition_v3a | ETH | 1h | 0.720 | 11.81% | 22.1241% | -19.8714% | 127 | -19.8714% | PASS |
| vortex_transition_v3a | BTC | 4h | 0.724 | 18.85% | 21.2885% | -19.9497% | 122 | -19.9497% | PASS |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.00% | 0.7259% | -0.7259% | 1 | -0.7259% | PASS |
| vortex_transition_v3b | ETH | 4h | 1.861 | 25.00% | 11.8547% | 61.2170% | 84 | 61.2170% | PASS |
| vortex_transition_v3b | ETH | 1h | 0.803 | 16.94% | 17.2546% | -15.1268% | 124 | -15.1268% | PASS |
| vortex_transition_v3b | BTC | 4h | 0.817 | 21.67% | 21.2812% | -13.4556% | 120 | -13.4556% | PASS |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |
| vortex_transition_v2c_btc | ETH | 4h | 1.867 | 25.00% | 12.4375% | 62.1264% | 84 | 62.1264% | PASS |
| vortex_transition_v2c_btc | ETH | 1h | 0.816 | 16.94% | 19.4136% | -14.0363% | 124 | -14.0363% | PASS |
| vortex_transition_v2c_btc | BTC | 4h | 0.733 | 21.67% | 20.5808% | -18.5550% | 120 | -18.5550% | PASS |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.00% | 0.9251% | -0.9251% | 1 | -0.9251% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| ichimoku_tk_transition_v1 | ETH | 4h | 0.692 | 2.011 | 2.781 |
| ichimoku_tk_transition_v1 | ETH | 1h | 0.270 | 1.004 | 0.571 |
| ichimoku_tk_transition_v1 | BTC | 4h | 1.641 | 1.102 | 0.819 |
| ichimoku_tk_transition_v1 | BTC | 1h | 0.000 | 0.000 | 0.000 |
| cci_chop_fade_v3 | ETH | 4h | 1.123 | 1.226 | 2.392 |
| cci_chop_fade_v3 | ETH | 1h | 0.856 | 1.172 | 0.000 |
| cci_chop_fade_v3 | BTC | 4h | 1.135 | 0.515 | 2.059 |
| cci_chop_fade_v3 | BTC | 1h | 0.000 | 0.000 | 0.000 |
| supertrend_obv_confirm_v1 | ETH | 4h | 0.840 | 1.237 | 1.301 |
| supertrend_obv_confirm_v1 | ETH | 1h | 0.885 | 1.156 | 0.999 |
| supertrend_obv_confirm_v1 | BTC | 4h | 0.745 | 0.754 | 1.251 |
| supertrend_obv_confirm_v1 | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v3a | ETH | 4h | 1.491 | 1.959 | 3.886 |
| vortex_transition_v3a | ETH | 1h | 0.926 | 0.837 | 0.195 |
| vortex_transition_v3a | BTC | 4h | 0.756 | 0.499 | 1.109 |
| vortex_transition_v3a | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v3b | ETH | 4h | 1.637 | 2.012 | 2.250 |
| vortex_transition_v3b | ETH | 1h | 1.206 | 0.828 | 0.129 |
| vortex_transition_v3b | BTC | 4h | 0.654 | 0.713 | 1.313 |
| vortex_transition_v3b | BTC | 1h | 0.000 | 0.000 | 0.000 |
| vortex_transition_v2c_btc | ETH | 4h | 1.552 | 1.909 | 2.986 |
| vortex_transition_v2c_btc | ETH | 1h | 1.228 | 0.846 | 0.128 |
| vortex_transition_v2c_btc | BTC | 4h | 0.699 | 0.632 | 0.985 |
| vortex_transition_v2c_btc | BTC | 1h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- None.

## Critical Comparison
- `ichimoku_tk_transition_v1` trades: **336** | avg PF: **0.851**
- `cci_chop_fade_v3` trades: **442** | avg PF: **0.803**
- Trade count difference: **-106**
