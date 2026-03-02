# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `chop_donchian_fade_v1`
- Status: COMPLETE
- Assets tested: BTC, ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per asset/timeframe)

| Asset | Timeframe | PF | Win Rate | Max DD % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| BTC | 1h | 0.000 | 0.00% | 0.00% | 0.00% | 0 | 0.00% | PASS |
| BTC | 4h | 0.000 | 0.00% | 0.00% | 0.00% | 0 | 0.00% | FAIL (`INSUFFICIENT_TRADES`) |
| ETH | 1h | 0.000 | 0.00% | 0.00% | 0.00% | 0 | 0.00% | PASS |
| ETH | 4h | 0.000 | 0.00% | 0.00% | 0.00% | 0 | 0.00% | FAIL (`INSUFFICIENT_TRADES`) |

## Regime Breakdown (PF)

| Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---:|---:|---:|---:|
| BTC | 1h | 0.000 | 0.000 | 0.000 |
| BTC | 4h | 0.000 | 0.000 | 0.000 |
| ETH | 1h | 0.000 | 0.000 | 0.000 |
| ETH | 4h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- BTC 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 0)
- ETH 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 0)

## Notes
- No entry signals fired in any test cell (0 long, 0 short across all four runs).
- Strategy produced no trades in this cycle; no realized PnL impact.
