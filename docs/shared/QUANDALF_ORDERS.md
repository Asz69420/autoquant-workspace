# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** IN PROGRESS
**Created:** 2026-03-03
**Thesis:** Move from pure backtest ranking to deterministic forward validation on ETH 4h champions with paper-trading state, weekly scorecard, and promotion queue.

### Active Forward-Test Roster (from docs/shared/CHAMPIONS.json)
- vortex_transition_v3a (ETH 4h) — active
- supertrend_tail_harvester_8to1 (ETH 4h) — active
- macd_tail_harvester_7to1_4h (ETH 4h) — pending_validation (canonical PF currently from 1h baseline)

### Forward-Test Operating Rules
- Runtime state/logs: `data/forward/*`
- Runner cadence: every 4h bar close at `:05` (AEST)
- Alerts: entry + close only (no no-signal spam)
- Health alert: trigger if no log entry for 2 consecutive cycles
- Weekly Sunday scorecard + leaderboard + promotion suggestions
- Promotion to active roster requires validated baseline and Quandalf review

---

## Archived Strategy Order (reference)

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
