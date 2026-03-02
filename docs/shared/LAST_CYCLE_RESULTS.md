# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `chop_donchian_fade_v2`
- Status: COMPLETE
- Assets tested: BTC, ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per asset/timeframe)

| Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | 1h | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | PASS |
| BTC | 4h | 0.000 | 0.00% | 1.2060% | -1.2060% | 1 | -1.2060% | FAIL (`INSUFFICIENT_TRADES`) |
| ETH | 1h | 0.000 | 0.00% | 0.9149% | -0.9149% | 1 | -0.9149% | PASS |
| ETH | 4h | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | FAIL (`INSUFFICIENT_TRADES`) |

## Regime Breakdown (PF)

| Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---:|---:|---:|---:|
| BTC | 1h | 0.000 | 0.000 | 0.000 |
| BTC | 4h | 0.000 | 0.000 | 0.000 |
| ETH | 1h | 0.000 | 0.000 | 0.000 |
| ETH | 4h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- BTC 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 1)
- ETH 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 0)

## Notes
- v2 generated first live signals versus v1 (2 total trades across matrix: BTC 4h short x1, ETH 1h short x1).
- Both realized trades were losers; PF remained 0.000 with low sample count.
