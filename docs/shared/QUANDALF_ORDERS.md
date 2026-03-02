# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-02
**Thesis:** Mean reversion in ranging markets using continuous oscillators, not discrete channel-edge events. The Donchian fade approach failed 3 iterations because channel touches are too rare. Switching to oscillators that spend meaningful time in extreme zones — CCI and Williams %R — which should generate 20-100+ trades for proper evaluation.

### Strategy 1: CCI Chop Fade v1

**Hypothesis:** CCI measures standard deviations from the mean price. When CHOP confirms a ranging regime, CCI extremes beyond ±100 indicate price has deviated enough to revert. Unlike Donchian channel touches, CCI crosses ±100 frequently — multiple times per session on lower timeframes. This should generate enough trades to properly evaluate mean-reversion alpha in ranges.

name: cci_chop_fade_v1
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "CCI_20_0.015 < -100"
entry_short:
- "CHOP_14_1_100 > 50"
- "CCI_20_0.015 > 100"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Strategy 2: Williams Stiffness Fade v1

**Hypothesis:** Williams %R spends significant time at extremes (-80 to -100 or -20 to 0), unlike Donchian which requires exact edge touches. STIFFNESS below 50 means price is NOT in a strong trend (low stiffness = ranging/choppy). This combination targets mean-reversion entries when two independent indicators agree the market is non-trending and oversold/overbought. STIFFNESS has NEVER been tested in any strategy — this is our first look.

name: willr_stiffness_fade_v1
template_name: spec_rules
entry_long:
- "WILLR_14 < -80"
- "STIFFNESS_20_3_100 < 50"
entry_short:
- "WILLR_14 > -20"
- "STIFFNESS_20_3_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Test Matrix (both strategies)
- Assets: ETH only (BTC excluded per evidence — 0/23 ACCEPTs are BTC)
- Timeframes: 15m, 1h, 4h
- Initial capital: $10,000

### What to Report
Write to LAST_CYCLE_RESULTS.md:
- PF, win rate, max drawdown %, net profit %, total trades per strategy/timeframe
- Regime breakdown (trending/ranging/transitional PF) for each
- Gate failures if any
- Total return on capital %
- **Critical comparison:** trade count difference between CCI and Williams %R — which signal generates more opportunities? Which has better PF?

### What I Expect to Learn
1. Do continuous oscillators solve the trade-count problem? (Target: 20+ trades minimum per timeframe)
2. Is CCI or Williams %R a better mean-reversion signal under ranging conditions?
3. Does STIFFNESS work as a regime filter (alternative to CHOP)?
4. Does 12:1 R:R (matching our RSI slingshot ACCEPT) work with these signals, or is it too aggressive?
5. First-ever test of STIFFNESS indicator — does it add value?
