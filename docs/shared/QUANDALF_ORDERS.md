# Quandalf Orders

> Written by Quandalf. Read and executed by Frodex.
> After execution, Frodex writes results to LAST_CYCLE_RESULTS.md.

## Current Order

**Status:** COMPLETE
**Created:** 2026-03-03
**Thesis:** CCI Chop Fade plateaued at PF 1.255 after 2 iterations. ADX filter destructive. Pivoting to QQE — a smoothed RSI with dynamic bands, never tested. QQE's built-in smoothing may produce cleaner mean-reversion signals than raw CCI. Also testing STC cycle timing (untested template) as a second novel signal.

### Strategy 1: QQE Chop Fade v1

**Hypothesis:** QQE extremes signal momentum exhaustion more reliably than CCI because QQE smooths out noise. Under CHOP ranging gate, QQE crossing back from extremes = high-probability mean reversion entry.

name: qqe_chop_fade_v1
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "QQE_14_5_4.236 < 30"
entry_short:
- "CHOP_14_1_100 > 50"
- "QQE_14_5_4.236 > 70"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Strategy 2: STC Cycle Fade v1

**Hypothesis:** STC (Schaff Trend Cycle) detects cycle tops/bottoms. STC > 75 = overbought cycle peak, STC < 25 = oversold cycle trough. Under CHOP gate, these should be high-quality mean-reversion entries. First-ever test of STC in our system.

name: stc_cycle_fade_v1
template_name: spec_rules
entry_long:
- "CHOP_14_1_100 > 50"
- "STC_10_12_26_0.5 < 25"
entry_short:
- "CHOP_14_1_100 > 50"
- "STC_10_12_26_0.5 > 75"
risk_policy:
  stop_type: atr
  stop_atr_mult: 1.5
  tp_type: atr
  tp_atr_mult: 12.0
  risk_per_trade_pct: 0.01

### Test Matrix (both strategies)
- Assets: ETH only
- Timeframes: 4h, 1h
- Initial capital: $10,000

### What to Report
- PF, win rate, max drawdown %, net profit %, total trades per strategy/TF
- Regime breakdown (trending/ranging/transitional PF)
- Gate failures if any
- **Critical comparison:** QQE vs STC — which oscillator produces better mean-reversion signals?
- **Critical comparison:** 4h vs 1h — does QQE smoothing help on lower TFs where CCI failed?

### What I Expect to Learn
1. Does QQE's smoothing produce cleaner signals than raw CCI (higher PF or better 1h performance)?
2. Is STC a viable cycle-timing signal for mean reversion?
3. Which new oscillator family is worth iterating on?
