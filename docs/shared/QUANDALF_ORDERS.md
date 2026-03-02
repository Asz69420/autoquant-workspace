# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-03
**Thesis:** v2c is the new #2 strategy after Supertrend 8:1. PF 1.892 on ETH 4h, 62.5% return, 12.3% DD, 84 trades — ALL regimes profitable (transitional PF 2.986). The optimization gradient is clear: tighter stop AND tighter TP both improved PF (v1 1.385 → v2a 1.735 → v2c 1.892). The reversal exit is the real edge — stops and TPs are just loss limiters. Push the frontier: find the floor on stop and TP tightening, and challenge ETH-only with the best params.

### Strategy 1: Vortex Transition v3a — Ultra-Tight Stop (13.3:1 R:R)

**Hypothesis:** v2c showed 1.0 ATR stop beats 1.25 ATR. The reversal exit catches winners before they need stop room. At 0.75 ATR, each of the ~57 losers costs 25% less per trade. If most winners survive 0.75 ATR drawdown before the reversal exit fires, PF should break 2.0. If PF drops, we've found the stop floor — winners need at least 1.0 ATR of breathing room.

name: vortex_transition_v3a
template_name: spec_rules
entry_long:
- "VTXP_14 crosses_above VTXM_14"
- "CHOP_14_1_100 < 50"
entry_short:
- "VTXM_14 crosses_above VTXP_14"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 0.75
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

### Strategy 2: Vortex Transition v3b — Tighter TP (8:1 R:R)

**Hypothesis:** v2c showed TP 10 beats TP 12 — tighter TP captured more profit from winners that would have reversed back down. At TP 8, even more winners should hit TP before reversal. Risk: the 3 monster tail trades (19-32% in v1) may have needed room past 8 ATR. If PF increases: 8:1 is the sweet spot and more winners are converting to TP hits. If PF drops: 10 was the floor — those tail runners need 10 ATR.

name: vortex_transition_v3b
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
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Strategy 3: Vortex Transition v2c on BTC — Assumption Challenge

**Hypothesis:** 0 BTC ACCEPTs across 706+ outcomes. But every prior BTC test used inferior strategies. v2c is our best signal — if BTC works anywhere, it works here. Vortex detects directional regime shifts, which should be asset-agnostic. If BTC PF > 1.0: the "ETH only" belief was a strategy quality issue, not an asset issue. If BTC loses: ETH superiority is confirmed with our strongest possible evidence.

name: vortex_transition_v2c_btc
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
- Assets: ETH for v3a/v3b, BTC for v2c_btc
- Timeframes: 4h only (1h confirmed dead across 6+ tests)
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades
- Regime breakdown (trending/ranging/transitional PF)
- **Critical comparisons:**
  - v3a vs v2c: Did 0.75 ATR stop kill winners or boost PF?
  - v3b vs v2c: Did TP 8 capture more or truncate tail runners?
  - v2c_btc vs v2c ETH: Is BTC viable with our best signal?
