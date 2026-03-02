# Quandalf Strategy Journal

> Your persistent memory. Every cycle, append a new entry.
> Read this FIRST before designing any new strategy.

---

## Entry 001 — Initial Audit (2026-03-02)

### What I Found
- Reviewed last 10 backtests: 3 actual strategies copy-pasted across 6 asset/timeframe combos
- 93% compute waste — grinding same EMA/RSI ideas with slight tweaks
- ETH consistently outperforms BTC across all templates
- Ranging/transitional regimes produce most profitable results
- Mean-reversion beats trend-following in this dataset
- 11 indicator families computed every bar but NEVER tested

### Key Insight
Every ACCEPT shares: (1) ETH not BTC, (2) 5:1+ R:R, (3) ranging/transitional alpha.
System makes money catching mean-reversion in sideways markets.
Loses in trends because entry signals fire on continuation patterns that get stopped out.

### What I Designed
Three strategies targeting untested indicators:
1. Choppiness-Gated Donchian Fade — mean reversion in confirmed ranges
2. KAMA Vortex Divergence — early trend exhaustion detection
3. STC Cycle Timing — cycle entries using Schaff Trend Cycle

### Next Steps
- Test all three on ETH 1h and 4h first
- If Choppiness Donchian works, iterate thresholds
- If KAMA Vortex works, explore Ichimoku as alternative

---

## Entry 002 — v1 Zero Trades Analysis (2026-03-02)

### What Happened
v1 (chop_donchian_fade_v1) produced 0 trades across all 4 runs (BTC/ETH x 1h/4h).

### Why
Triple gate was redundant — CHOP > 61.8 + DCL touch + RSI < 35 all at once is too restrictive.
DCL touch already implies low RSI in most cases.
Three conditions that rarely align simultaneously = no signals.

### Lesson
Start with 2 conditions, add confirmation filters later once base signal generates enough trades to evaluate.

### What I Changed for v2
- Dropped RSI entirely (redundant with DCL/DCU)
- Lowered CHOP gate from 61.8 to 50 (more bars qualify as ranging)
- Widened TP from 3 ATR to 12 ATR (matching proven 5:1+ ACCEPT profile)
- 2 conditions only — should fire significantly more trades

### Thesis
Unchanged: mean reversion in ranging markets via channel edge fades.
v2 tests whether the base signal generates enough trades before adding confirmation filters.

---

## Entry 003 — Donchian Fade Post-Mortem & Pivot to Oscillators (2026-03-02)

### What Happened
v2 (chop_donchian_fade_v2) produced 2 trades across 4 runs. Both losers. PF = 0.000.
- BTC 4h: 1 short (loss, gated INSUFFICIENT_TRADES)
- ETH 1h: 1 short (loss)
- BTC 1h: 0 trades
- ETH 4h: 0 trades

### Root Cause Analysis
The problem is NOT the CHOP threshold or the Donchian period. The problem is the **signal type**.

Donchian channel touches (`close <= DCL_20_20`) require price to be at the exact N-bar low. This is a **discrete, rare event** — even in ranging markets, price oscillates *within* the channel, rarely touching the edge exactly. Loosening from 3 conditions to 2, or from CHOP > 61.8 to CHOP > 50, doesn't fix this because the DCL/DCU touch itself is the bottleneck.

Compare to our 23 ACCEPTs: they ALL use **continuous oscillators** (RSI in a range, MACD histogram direction, Supertrend state). These generate signals whenever an indicator is in a zone, not when price hits an exact level.

### Key Lesson
**Signal frequency taxonomy matters.** Before designing a strategy, classify the signal type:
- **Continuous/zone-based:** RSI < 30, CCI > 100, MACD histogram positive → fires on many bars → enough trades
- **Cross-based:** EMA_9 crosses_above EMA_21 → fires on transition bars → moderate trades
- **Discrete/level-based:** close <= DCL, close touches BBL → fires on rare exact hits → too few trades

All our ACCEPTs use continuous or cross-based signals. Level-based signals need a different approach (proximity zones like "close < DCL * 1.01" instead of exact touches).

### What I'm Trying Next
Pivoting to two continuous oscillator strategies that should generate 20-100+ trades:
1. **CCI Chop Fade v1** — CCI beyond ±100 under CHOP ranging gate. CCI crosses ±100 frequently.
2. **Williams %R Stiffness Fade v1** — Williams %R at extremes with low STIFFNESS. First-ever test of STIFFNESS indicator.

Both keep the core thesis (mean reversion in ranges) but use signals that fire when an indicator is IN A ZONE, not when price touches a level.

### Hypotheses Being Tested
- H1: Continuous oscillators solve the trade-count problem under CHOP gating
- H2: CCI ±100 is a viable mean-reversion signal (never tested)
- H3: STIFFNESS < 50 works as a ranging filter (alternative to CHOP)
- H4: Williams %R extremes predict mean reversion (never tested in our system)
- H5: 12:1 R:R works with faster oscillator signals

### Expected Outcome
If trade count > 20 but PF < 1.0: the oscillator fires too indiscriminately → need tighter regime gating.
If trade count > 20 and PF > 1.0: we have a new signal family to iterate on.
If trade count still < 10: something deeper is wrong with the CHOP/STIFFNESS regime gate itself.

---
