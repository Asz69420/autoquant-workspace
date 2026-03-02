# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `cci_chop_fade_v1` + `willr_stiffness_fade_v1`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 15m, 1h, 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| cci_chop_fade_v1 | ETH | 15m | 0.617 | 10.62% | 35.5475% | -25.1388% | 113 | -25.1388% | PASS |
| cci_chop_fade_v1 | ETH | 1h | 0.808 | 15.50% | 51.1917% | -22.3100% | 129 | -22.3100% | PASS |
| cci_chop_fade_v1 | ETH | 4h | 1.255 | 36.87% | 16.3846% | 28.9503% | 179 | 28.9503% | PASS |
| willr_stiffness_fade_v1 | ETH | 15m | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | PASS |
| willr_stiffness_fade_v1 | ETH | 1h | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | PASS |
| willr_stiffness_fade_v1 | ETH | 4h | 0.000 | 0.00% | 0.0000% | 0.0000% | 0 | 0.0000% | FAIL (`INSUFFICIENT_TRADES`) |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| cci_chop_fade_v1 | ETH | 15m | 0.918 | 0.000 | 0.160 |
| cci_chop_fade_v1 | ETH | 1h | 0.871 | 0.484 | 0.838 |
| cci_chop_fade_v1 | ETH | 4h | 1.132 | 1.430 | 1.521 |
| willr_stiffness_fade_v1 | ETH | 15m | 0.000 | 0.000 | 0.000 |
| willr_stiffness_fade_v1 | ETH | 1h | 0.000 | 0.000 | 0.000 |
| willr_stiffness_fade_v1 | ETH | 4h | 0.000 | 0.000 | 0.000 |

## Gate Failures
- willr_stiffness_fade_v1 ETH 4h: `INSUFFICIENT_TRADES` (min required: 10, observed: 0)

## Critical Comparison: CCI vs Williams %R
- Trade count (all tested timeframes):
  - `cci_chop_fade_v1`: **421 trades** (113 + 129 + 179)
  - `willr_stiffness_fade_v1`: **0 trades**
- Difference: **+421 trades** in favor of CCI.
- PF comparison:
  - CCI per-timeframe PF: 0.617 / 0.808 / 1.255 (avg 0.893)
  - Williams %R per-timeframe PF: 0.000 / 0.000 / 0.000 (avg 0.000)
- Verdict: **CCI generated vastly more opportunities and materially better performance than Williams %R in this cycle.**

## Notes
- Continuous oscillator hypothesis was confirmed for CCI (trade frequency solved).
- STIFFNESS + Williams %R produced no qualifying entries on this ETH matrix and needs threshold/logic revision before retest.
