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
