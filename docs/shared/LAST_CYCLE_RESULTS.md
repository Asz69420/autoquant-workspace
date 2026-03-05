# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `supertrend_cci_v4_4h_8to1` + `supertrend_cci_v4_4h_tight` + `kama_vortex_div_v1` + `kama_vortex_div_v1_10to1` + `ema200_vortex_v3b_8to1` + `ema200_vortex_v3b_10to1` + `ema200_vortex_v3_8to1`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| supertrend_cci_v4_4h_8to1 | ETH | 4h | 1.358 | 17.62% | 25.3579% | 69.2541% | 193 | 69.2541% | PASS |
| supertrend_cci_v4_4h_tight | ETH | 4h | 1.179 | 14.85% | 26.8630% | 38.4450% | 202 | 38.4450% | PASS |
| kama_vortex_div_v1 | ETH | 4h | 0.000 | 0.00% | 9.5068% | -9.5068% | 9 | -9.5068% | FAIL (`INSUFFICIENT_TRADES`) |
| kama_vortex_div_v1_10to1 | ETH | 4h | 0.000 | 0.00% | 9.5068% | -9.5068% | 9 | -9.5068% | FAIL (`INSUFFICIENT_TRADES`) |
| ema200_vortex_v3b_8to1 | ETH | 4h | 1.046 | 10.77% | 25.5630% | 6.4669% | 130 | 6.4669% | PASS |
| ema200_vortex_v3b_10to1 | ETH | 4h | 1.358 | 11.61% | 32.2035% | 48.9602% | 112 | 48.9602% | PASS |
| ema200_vortex_v3_8to1 | ETH | 4h | 1.046 | 10.77% | 25.5630% | 6.4669% | 130 | 6.4669% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| supertrend_cci_v4_4h_8to1 | ETH | 4h | 0.742 | 1.548 | 3.291 |
| supertrend_cci_v4_4h_tight | ETH | 4h | 0.779 | 1.433 | 1.764 |
| kama_vortex_div_v1 | ETH | 4h | 0.000 | 0.000 | 0.000 |
| kama_vortex_div_v1_10to1 | ETH | 4h | 0.000 | 0.000 | 0.000 |
| ema200_vortex_v3b_8to1 | ETH | 4h | 0.417 | 1.505 | 1.476 |
| ema200_vortex_v3b_10to1 | ETH | 4h | 0.574 | 1.751 | 2.297 |
| ema200_vortex_v3_8to1 | ETH | 4h | 0.417 | 1.505 | 1.476 |

## Gate Failures
- kama_vortex_div_v1 ETH 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 9)
- kama_vortex_div_v1_10to1 ETH 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 9)

## Critical Comparison
- `supertrend_cci_v4_4h_8to1` trades: **193** | avg PF: **1.358**
- `supertrend_cci_v4_4h_tight` trades: **202** | avg PF: **1.179**
- Trade count difference: **-9**
