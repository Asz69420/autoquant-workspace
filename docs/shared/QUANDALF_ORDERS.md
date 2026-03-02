# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-03
**Thesis:** CCI Chop Fade ETH 4h hit PF 1.255 with all regimes profitable — close to ACCEPT. Two refinements: (1) tighten R:R from 12:1 to 8:1 to boost win rate, (2) add ADX < 25 to filter out trending bars where mean reversion fails.

### Strategy 1: CCI Chop Fade v2 (tighter R:R)

**Hypothesis:** 12:1 R:R requires massive moves to hit TP. At 8:1 (matching our Supertrend champion), more winners should close profitably, pushing PF above 1.3.

name: cci_chop_fade_v2
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

### Strategy 2: CCI ADX Chop Fade v1 (ADX confirmation)

**Hypothesis:** Adding ADX < 25 as a trend-absence filter should cut entries during trending bars (where v1 had weakest PF 1.13) while preserving ranging/transitional alpha.

name: cci_adx_chop_fade_v1
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "ADX_14 < 25"
- "CCI_20_0.015 < -100"
entry_short:
- "CHOP_14_1_100 > 50"
- "ADX_14 < 25"
- "CCI_20_0.015 > 100"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix (both strategies)
- Assets: ETH only
- Timeframes: 4h only (lower TFs confirmed losers)
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades per strategy
- Regime breakdown (trending/ranging/transitional PF)
- Gate failures if any
- **Critical comparison:** v2 (8:1 R:R) vs v1 baseline (PF 1.255). Did tighter R:R boost PF?
- **Critical comparison:** ADX-filtered vs unfiltered. Did ADX cut trending losers without killing trade count?

### What I Expect to Learn
1. Does 8:1 R:R push CCI Chop Fade past ACCEPT threshold (PF > 1.3)?
2. Does ADX < 25 improve regime selectivity without over-filtering?
3. Which refinement path is more promising for v3?
