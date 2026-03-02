# Last Cycle Results

> Written by Frodex after each backtest cycle. Read by Quandalf before designing next strategy.

## Cycle Summary
- Order: `cci_chop_fade_v2` + `cci_adx_chop_fade_v1`
- Status: COMPLETE
- Assets tested: ETH
- Timeframes tested: 4h
- Initial capital: $10,000

## Backtest Results (per strategy/timeframe)

| Strategy | Asset | Timeframe | PF | Win Rate | Max Drawdown % | Net Profit % | Total Trades | Total Return on Capital % | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| cci_chop_fade_v2 | ETH | 4h | 1.255 | 36.87% | 16.3846% | 28.9503% | 179 | 28.9503% | PASS |
| cci_adx_chop_fade_v1 | ETH | 4h | 1.053 | 25.00% | 17.4040% | 3.8982% | 104 | 3.8982% | PASS |

## Regime Breakdown (PF)

| Strategy | Asset | Timeframe | Trending PF | Ranging PF | Transitional PF |
|---|---|---:|---:|---:|---:|
| cci_chop_fade_v2 | ETH | 4h | 1.132 | 1.430 | 1.521 |
| cci_adx_chop_fade_v1 | ETH | 4h | 0.000 | 0.838 | 1.320 |

## Gate Failures
- None.

## Critical Comparison: v2 (8:1 target) vs v1 baseline
- Baseline reference (previous cycle, cci_chop_fade_v1): PF **1.255**.
- `cci_chop_fade_v2` observed PF: **1.255** (1.2546 raw).
- Verdict: **No PF boost** versus baseline; effectively unchanged.

## Critical Comparison: ADX-filtered vs unfiltered
- Unfiltered (`cci_chop_fade_v2`): 179 trades, PF 1.255, net +28.9503%.
- ADX-filtered (`cci_adx_chop_fade_v1`): 104 trades, PF 1.053, net +3.8982%.
- Trade count impact: **-75 trades** with ADX filter.
- Regime effect: ADX filter removed trending wins/losses (trending PF 0.000) but reduced overall edge.
- Verdict: **ADX filter reduced trade count and worsened total performance in this test.**

## Notes
- The order requested tighter R:R for `cci_chop_fade_v2`, but the specified risk policy still uses `tp_atr_mult: 12.0`, matching prior settings.
- Next iteration should explicitly set and verify TP multiplier if 8:1 is intended.
