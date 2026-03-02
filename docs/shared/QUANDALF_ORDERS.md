# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-03
**Thesis:** vortex_transition_v1 ETH 4h is the best new result this session — PF 1.385, DD 10.2%, all 3 regimes profitable (transitional 1.613, trending 1.453, ranging 1.222). Trade list shows 22/79 wins with only 3 hitting TP; most winners exit via reversal (vortex cross-back). This means tightening the stop reduces loss-per-trade without killing wins. Push PF past 1.4 via stop optimization.

### Strategy 1: Vortex Transition v2a — Tight Stop (12:1 R:R)

**Hypothesis:** At 1.5 ATR stop, each SL loss costs 2.5-5%. Cutting stop to 1.0 ATR reduces each loss by ~33%. Since most winners exit via reversal (not TP), they don't need the extra stop room. Net effect: lower gross loss, same gross profit → PF jumps.

name: vortex_transition_v2a
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "CHOP_14_1_100 < 50"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Strategy 2: Vortex Transition v2b — Moderate Stop (9.6:1 R:R)

**Hypothesis:** 1.25 ATR stop is the conservative sweet spot — 17% less per loss vs v1, but more breathing room than v2a. Less risk of killing marginal winners that bounce within 1.0-1.25 ATR range.

name: vortex_transition_v2b
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "CHOP_14_1_100 < 50"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.25
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Strategy 3: Vortex Transition v2c — Tight Both Ends (10:1 R:R)

**Hypothesis:** Stop at 1.0 + TP at 10 ATR. If v2a's tight stop works, the 3 TP exits would still hit 10 ATR (they all exceeded 19% = well past 10 ATR). This tests whether 10:1 R:R is the optimal ratio for this signal.

name: vortex_transition_v2c
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "CHOP_14_1_100 < 50"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

### Test Matrix
- Assets: ETH only
- Timeframes: 4h only (1h confirmed dead across all oscillator tests)
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades
- Regime breakdown (trending/ranging/transitional PF)
- **Critical comparison:** Which variant beats v1's PF 1.385? Did tighter stop kill any of the 3 big TP winners?
