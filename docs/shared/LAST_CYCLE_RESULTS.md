# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `qqe_chop_fade_v1` + `stc_cycle_fade_v1`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| qqe_chop_fade_v1 | ETH | 4h | 0.116 | 3.03% | 25.4202% | -25.4202% | 33 | -25.4202% | PASS |
| qqe_chop_fade_v1 | ETH | 1h | 0.993 | 15.15% | 18.7665% | -0.2201% | 33 | -0.2201% | PASS |
| stc_cycle_fade_v1 | ETH | 4h | 1.012 | 36.28% | 33.8095% | 1.8678% | 215 | 1.8678% | PASS |
| stc_cycle_fade_v1 | ETH | 1h | 0.809 | 31.54% | 44.5884% | -30.2846% | 260 | -30.2846% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| qqe_chop_fade_v1 | ETH | 4h | 0.116 | 0.000 | 0.000 |
| qqe_chop_fade_v1 | ETH | 1h | 1.036 | 0.000 | 0.000 |
| stc_cycle_fade_v1 | ETH | 4h | 0.911 | 1.038 | 1.280 |
| stc_cycle_fade_v1 | ETH | 1h | 0.634 | 0.895 | 1.246 |

## Gate Failures
- None.

## Critical Comparison
- `qqe_chop_fade_v1` trades: **66** | avg PF: **0.555**
- `stc_cycle_fade_v1` trades: **475** | avg PF: **0.911**
- Trade count difference: **-409**
