# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** NEW
**Created:** 2026-03-03
**Thesis:** With forward-testing live, shift to portfolio diversification. Current champions (Vortex + Supertrend) are both cross-based trend detectors — correlated exposure. Need decorrelated signal families to build a robust portfolio. Testing Ichimoku transitions (independent math from Vortex) and CCI iteration (mean-reversion component).

### Forward-Test Status (MONITOR — no action needed)
- vortex_transition_v3a (ETH 4h) — ACTIVE, 2 clean cycles, 0 trades, flat
- supertrend_tail_harvester_8to1 (ETH 4h) — ACTIVE, 2 clean cycles, 0 trades, flat
- Forward runner, health monitor, and weekly scorecard: all operational

### Strategy 1: Ichimoku Tenkan-Kijun Transition v1

**Hypothesis:** Vortex crossover detects directional transitions via VTXP/VTXM momentum ratio. Ichimoku Tenkan-Kijun cross detects transitions via median price over different lookback windows (9 vs 26 bars). If BOTH detect transitions profitably, the edge isn't Vortex-specific — it's a general property of regime shifts on ETH 4h. If Ichimoku fails, Vortex has a unique structural advantage.

The CHOP < 50 gate keeps us out of choppy ranges where crosses whipsaw.

name: ichimoku_tk_transition_v1
template_name: spec_rules
entry_long:
- "ITS_9 crosses_above IKS_26"
- "CHOP_14_1_100 < 50"
entry_short:
- "ITS_9 crosses_below IKS_26"
- "CHOP_14_1_100 < 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 0.75
  tp_type: atr
  tp_atr_mult: 10.0
  risk_per_trade_pct: 0.01

### Strategy 2: CCI Chop Fade v3 — Actual 8:1 R:R Test

**Hypothesis:** CCI Chop Fade v1 hit PF 1.255 with 12:1 R:R. v2 was supposed to test 8:1 but was accidentally submitted with 12:1 (same result). A properly configured 8:1 R:R should increase win rate by converting more winners to TP hits (same thesis as Vortex v3b TP=8 test). If PF > 1.3, CCI becomes promotion-eligible as a mean-reversion complement to the transition-detection champions.

name: cci_chop_fade_v3
template_name: spec_rules
entry_long:
- "CCI_20_0.015 < -100"
- "CHOP_14_1_100 > 50"
entry_short:
- "CCI_20_0.015 > 100"
- "CHOP_14_1_100 > 50"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Strategy 3: OBV Momentum Confirmation v1

**Hypothesis:** Every strategy we've tested uses only price-derived indicators. OBV is computed but never tested. Volume precedes price — if OBV is rising while price dips, it signals accumulation (bullish). Combining Supertrend direction (trend state) with OBV confirmation (volume conviction) should filter out false breakouts. Test whether volume adds signal quality.

Note: OBV is an absolute cumulative value. We need a relative measure. Use OBV > SMA_20 proxy for rising OBV (OBV above its own smoothed average). **If OBV vs SMA comparison is not directly available in the dataframe, skip this strategy and note the gap.**

name: supertrend_obv_confirm_v1
template_name: spec_rules
entry_long:
- "SUPERTd_7_3.0 == 1"
- "ADX_14 > 15"
entry_short:
- "SUPERTd_7_3.0 == -1"
- "ADX_14 > 15"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.0
  tp_type: atr
  tp_atr_mult: 8.0
  risk_per_trade_pct: 0.01

### Test Matrix
- Assets: ETH only (BTC confirmed dead across 6+ tests with our best signals)
- Timeframes: 4h only (1h confirmed dead across 10+ tests)
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades
- Regime breakdown (trending/ranging/transitional PF)
- **Critical comparisons:**
  - Ichimoku v1 vs Vortex v3a: Is transition detection a general edge or Vortex-specific?
  - CCI v3 vs CCI v1: Does 8:1 R:R actually improve PF over 12:1?
  - OBV confirm vs plain Supertrend: Does volume add signal quality? (or note if OBV comparison unavailable)

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
