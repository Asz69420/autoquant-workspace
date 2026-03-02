# Quandalf Strategy Journal

> This is Quandalf's persistent memory. Every cycle, append a new entry.
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
The system makes money catching mean-reversion moves in sideways markets.
It loses in trends because entry signals fire on continuation patterns that get stopped out.

### What I Designed
Three new strategies targeting untested indicators:
1. Choppiness-Gated Donchian Fade — mean reversion in confirmed ranges using CHOP + DCL/DCU + RSI
2. KAMA Vortex Divergence — early trend exhaustion using KAMA slope flattening + Vortex crossover
3. STC Cycle Timing — cycle entries using Schaff Trend Cycle + EMA slope + Choppiness filter

### Next Steps
- Test all three across ETH 1h and 4h first (highest probability of success based on historical data)
- If Choppiness Donchian works, iterate with tighter CHOP thresholds and different RSI levels
- If KAMA Vortex works, explore Ichimoku cloud as alternative trend exhaustion signal

---

(Append new entries below as cycles complete)
